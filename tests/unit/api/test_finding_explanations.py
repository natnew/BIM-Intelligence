"""``POST /reviews/{runId}/findings/{findingId}/explanation``.

Covers FR-EXP-03, FR-EXP-05, FR-AI-01, ADR-009, C-01 and C-02. Every test is offline: the LLM
is either off, a :class:`FakeClient`, or a :class:`LiveClient`
over a stub SDK object. The endpoint must verify run, finding, check, requirement, source and
model provenance before any evidence is assembled, label every fallback, and never write to
``run.json`` or ``findings.json``.
"""

from __future__ import annotations

import hashlib
import json
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bim_intelligence.api.deps import get_llm_client
from bim_intelligence.api.main import API_PREFIX
from bim_intelligence.config import Settings
from bim_intelligence.llm import client as llm_client_module
from bim_intelligence.llm.client import FakeClient, LiveClient, LLMClient
from bim_intelligence.llm.factory import create_budget_ledger
from bim_intelligence.schemas import CheckSpec, Requirement, RequirementSource
from bim_intelligence.store import MODEL_INDEX_FILE, SessionStore
from bim_intelligence.store.session_store import FINDINGS_FILE, MODELS_DIR, RUN_FILE, RUNS_DIR
from fixtures.make_minimal_ifc import GLOBAL_IDS
from fixtures.variants import add_misclassified_w002_type, write_variant
from support.api import FIXTURE_BYTES, assert_problem, upload
from support.ids import FIXTURE_IDS_BYTES, upload_ids
from support.llm_stub import CapturingCompletions, live_settings, stub_live_client

FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()
UNKNOWN_RUN = "6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b"
UNKNOWN_SESSION = "0a1b2c3d-4e5f-4a6b-9c7d-8e9f0a1b2c3d"


@pytest.fixture
def review_session(client: TestClient, loaded_session: str) -> str:
    assert upload_ids(client, loaded_session, FIXTURE_IDS_BYTES).status_code == 201
    return loaded_session


@pytest.fixture
def store(settings: Settings) -> SessionStore:
    return SessionStore(settings.data_dir / "sessions")


def _use(client: TestClient, factory: Callable[[], LLMClient | None]) -> None:
    cast(FastAPI, client.app).dependency_overrides[get_llm_client] = factory


def _review(client: TestClient, session_id: str, objective: str | None = None) -> dict[str, Any]:
    kwargs: dict[str, Any] = (
        {"json": {"objective": objective, "ai_required": False}} if objective else {}
    )
    response = client.post(f"{API_PREFIX}/sessions/{session_id}/reviews", **kwargs)
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def _findings(client: TestClient, session_id: str, run_id: str) -> list[dict[str, Any]]:
    response = client.get(f"{API_PREFIX}/sessions/{session_id}/findings", params={"run_id": run_id})
    assert response.status_code == 200, response.text
    return cast(list[dict[str, Any]], response.json())


def _fire_finding(client: TestClient, session_id: str, run_id: str) -> dict[str, Any]:
    return next(
        finding
        for finding in _findings(client, session_id, run_id)
        if finding["elements"][0]["global_id"] == GLOBAL_IDS["W-002"]
    )


def _explain(
    client: TestClient, session_id: str, run_id: str, finding_id: str, **headers: str
) -> Any:
    return client.post(
        f"{API_PREFIX}/sessions/{session_id}/reviews/{run_id}/findings/{finding_id}/explanation",
        headers=headers,
    )


def _grounded(finding: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    element = finding["elements"][0]
    draft: dict[str, Any] = {
        "finding_id": finding["id"],
        "summary": f"{finding['observed']}; the verified check expected {finding['expected']}.",
        "probable_cause": "The deterministic check found the required property missing.",
        "corrective_action": "Add the required property to the cited wall and re-run the review.",
        "citations": [
            {
                "finding_id": finding["id"],
                "global_id": element["global_id"],
                "requirement_id": finding["requirement_id"],
                "rule_id": finding["rule_id"],
                "expected": finding["expected"],
                "observed": finding["observed"],
            }
        ],
    }
    draft.update(overrides)
    return draft


def _run_dir(settings: Settings, session_id: str, run_id: str) -> Path:
    return settings.data_dir / "sessions" / session_id / RUNS_DIR / run_id


def _index_path(settings: Settings, session_id: str, model_hash: str = FIXTURE_SHA256) -> Path:
    return settings.data_dir / "sessions" / session_id / MODELS_DIR / model_hash / MODEL_INDEX_FILE


def _rewrite_json(path: Path, mutate: Callable[[Any], None]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _replace_requirement(
    store: SessionStore, session_id: str, requirement_id: str, **changes: Any
) -> None:
    requirements = store.read_requirements(session_id)
    updated = [
        Requirement.model_validate({**item.model_dump(), **changes})
        if item.id == requirement_id
        else item
        for item in requirements
    ]
    with store.lock_model(session_id) as lock:
        store.write_requirements(lock, updated)


# -- labelled outcomes --------------------------------------------------------------------


def test_grounded_ai_explanation_is_labelled_and_leaves_run_files_untouched(
    client: TestClient, settings: Settings, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    run_dir = _run_dir(settings, review_session, run["id"])
    files_before = sorted(path.name for path in run_dir.iterdir())
    before = {name: (run_dir / name).read_bytes() for name in (RUN_FILE, FINDINGS_FILE)}
    _use(client, lambda: FakeClient([_grounded(finding)], model="muse-spark-1.3"))

    response = _explain(client, review_session, run["id"], finding["id"])

    assert response.status_code == 200, response.text
    explanation = response.json()
    assert explanation["source"] == "ai_generated"
    assert explanation["grounding_status"] == "passed"
    assert explanation["fallback_reason"] is None
    assert explanation["model"] == "muse-spark-1.3"
    assert explanation["finding_id"] == finding["id"]
    assert explanation["citations"] == _grounded(finding)["citations"]
    assert {name: (run_dir / name).read_bytes() for name in before} == before
    assert sorted(path.name for path in run_dir.iterdir()) == files_before


def test_ai_disabled_returns_a_labelled_deterministic_template(
    client: TestClient, settings: Settings, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    findings_before = (_run_dir(settings, review_session, run["id"]) / FINDINGS_FILE).read_bytes()

    response = _explain(client, review_session, run["id"], finding["id"])

    assert response.status_code == 200, response.text
    explanation = response.json()
    assert explanation["source"] == "deterministic_template"
    assert explanation["grounding_status"] == "fallback"
    assert explanation["fallback_reason"] == "ai_disabled"
    assert explanation["model"] is None
    assert explanation["citations"][0]["global_id"] == GLOBAL_IDS["W-002"]
    assert finding["observed"] in explanation["summary"]
    after = (_run_dir(settings, review_session, run["id"]) / FINDINGS_FILE).read_bytes()
    assert after == findings_before


def test_ungrounded_ai_output_falls_back_with_grounding_failed(
    client: TestClient, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    invented = _grounded(finding, corrective_action="Set FireRating to 90 minutes.")
    _use(client, lambda: FakeClient([invented]))

    explanation = _explain(client, review_session, run["id"], finding["id"]).json()

    assert explanation["source"] == "deterministic_template"
    assert explanation["fallback_reason"] == "grounding_failed"
    assert "90" not in explanation["corrective_action"]


def test_citation_for_another_element_falls_back_with_grounding_failed(
    client: TestClient, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    mixed = _grounded(finding)
    mixed["citations"][0]["global_id"] = GLOBAL_IDS["W-003"]
    _use(client, lambda: FakeClient([mixed]))

    explanation = _explain(client, review_session, run["id"], finding["id"]).json()

    assert explanation["fallback_reason"] == "grounding_failed"
    assert explanation["citations"][0]["global_id"] == GLOBAL_IDS["W-002"]


def test_schema_invalid_ai_output_falls_back_with_ai_output_invalid(
    client: TestClient, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    _use(client, lambda: FakeClient([{"finding_id": finding["id"], "summary": "Only this."}]))

    explanation = _explain(client, review_session, run["id"], finding["id"]).json()

    assert explanation["source"] == "deterministic_template"
    assert explanation["fallback_reason"] == "ai_output_invalid"


# -- live client over a stub SDK (no network) ---------------------------------------------


def test_default_configuration_never_constructs_an_sdk_client_or_leaves_loopback(
    client: TestClient, review_session: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def refuse_sdk(*args: object, **kwargs: object) -> None:
        raise AssertionError("The default offline configuration constructed a provider client.")

    real_connect = socket.socket.connect

    def loopback_only(sock: socket.socket, address: Any) -> None:
        # Windows' asyncio event loop builds its self-pipe over a loopback socket pair.
        host = address[0] if isinstance(address, tuple) else address
        if host not in {"127.0.0.1", "::1"}:
            raise AssertionError(f"The default offline configuration connected to {host!r}.")
        real_connect(sock, address)

    monkeypatch.setattr(llm_client_module, "OpenAI", refuse_sdk)
    monkeypatch.setattr(socket.socket, "connect", loopback_only)

    run = _review(client, review_session, objective="Check fire ratings only")
    finding = _fire_finding(client, review_session, run["id"])
    explanation = _explain(client, review_session, run["id"], finding["id"]).json()

    assert run["plan_source"] == "default"
    assert [result["status"] for result in run["check_results"]] == ["failed", "failed"]
    assert explanation["fallback_reason"] == "ai_disabled"
    # The guard is live: an unstubbed LiveClient would have been refused.
    with pytest.raises(AssertionError, match="constructed a provider client"):
        LiveClient(live_settings(tmp_path), ledger=create_budget_ledger(live_settings(tmp_path)))


def _use_stub_live_client(
    client: TestClient, settings: Settings, completions: CapturingCompletions
) -> None:
    _use(client, lambda: stub_live_client(settings, completions))


def test_budget_rejection_falls_back_before_any_provider_request(
    client: TestClient, review_session: str, tmp_path: Path
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    completions = CapturingCompletions(json.dumps(_grounded(finding)))
    tiny = "0.00001"
    live = live_settings(
        tmp_path,
        llm_project_budget_usd=tiny,
        llm_max_run_budget_usd=tiny,
        llm_max_call_budget_usd=tiny,
    )
    _use_stub_live_client(client, live, completions)

    explanation = _explain(client, review_session, run["id"], finding["id"]).json()

    assert explanation["source"] == "deterministic_template"
    assert explanation["fallback_reason"] == "budget_limit"
    assert completions.requests == []


def test_per_run_call_cap_stops_a_second_paid_explanation(
    client: TestClient, review_session: str, tmp_path: Path
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    completions = CapturingCompletions(json.dumps(_grounded(finding)))
    _use_stub_live_client(client, live_settings(tmp_path, llm_max_calls_per_run=1), completions)

    first = _explain(client, review_session, run["id"], finding["id"]).json()
    second = _explain(client, review_session, run["id"], finding["id"]).json()

    assert first["source"] == "ai_generated"
    assert first["model"] == "muse-spark-1.3"
    assert second["fallback_reason"] == "budget_limit"
    assert len(completions.requests) == 1
    request = completions.requests[0]
    assert request["model"] == "muse-spark-1.3"
    assert request["response_format"] == {"type": "json_object"}
    assert request["max_tokens"] == 500
    evidence = json.loads(request["messages"][1]["content"])
    assert evidence["finding"]["id"] == finding["id"]
    assert [record["ref"]["global_id"] for record in evidence["model_index_elements"]] == [
        GLOBAL_IDS["W-002"]
    ]


# -- request validation and provenance ----------------------------------------------------


def test_unknown_finding_and_finding_from_another_run_are_404(
    client: TestClient, review_session: str
) -> None:
    full = _review(client, review_session)
    classification = next(
        finding
        for finding in _findings(client, review_session, full["id"])
        if finding["elements"][0]["global_id"] == GLOBAL_IDS["W-003"]
    )
    requirements = client.get(f"{API_PREFIX}/sessions/{review_session}/requirements").json()
    fire_check = next(item["check"]["id"] for item in requirements if item["id"] == "REQ-001")
    _use(
        client,
        lambda: FakeClient([{"checks": [{"check_id": fire_check, "reason": "Fire safety."}]}]),
    )
    narrow = _review(client, review_session, objective="Check fire ratings only")
    assert narrow["plan_source"] == "llm"
    assert classification["id"] not in narrow["check_results"][0]["finding_ids"]

    other_run = _explain(client, review_session, narrow["id"], classification["id"])
    unknown = _explain(client, review_session, full["id"], "f" * 64)

    assert_problem(other_run, 404, "finding-not-found")
    assert_problem(unknown, 404, "finding-not-found")


def test_unknown_or_malformed_run_and_session_are_rejected(
    client: TestClient, review_session: str
) -> None:
    run = _review(client, review_session)
    finding_id = run["check_results"][0]["finding_ids"][0]

    assert_problem(_explain(client, review_session, UNKNOWN_RUN, finding_id), 404, "run-not-found")
    assert_problem(_explain(client, review_session, "not-a-run", finding_id), 400, "invalid-run-id")
    other_session = client.post(f"{API_PREFIX}/sessions").json()["id"]
    assert_problem(_explain(client, other_session, run["id"], finding_id), 404, "run-not-found")
    assert_problem(
        _explain(client, UNKNOWN_SESSION, run["id"], finding_id), 404, "session-not-found"
    )
    assert_problem(
        _explain(client, "not-a-session", run["id"], finding_id), 400, "invalid-session-id"
    )


def test_run_recorded_for_another_session_is_409(
    client: TestClient, settings: Settings, review_session: str
) -> None:
    run = _review(client, review_session)
    finding_id = run["check_results"][0]["finding_ids"][0]
    _rewrite_json(
        _run_dir(settings, review_session, run["id"]) / RUN_FILE,
        lambda payload: payload.update(session_id="another-session"),
    )

    response = _explain(client, review_session, run["id"], finding_id)

    assert_problem(
        response, 409, "explanation-provenance-mismatch", detail_contains="different session"
    )


def test_t5_run_identity_mismatch_is_rejected_before_explanation(
    client: TestClient, settings: Settings, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    _rewrite_json(
        _run_dir(settings, review_session, run["id"]) / RUN_FILE,
        lambda payload: payload.update(id=UNKNOWN_RUN),
    )
    ai = FakeClient([_grounded(finding)])
    _use(client, lambda: ai)

    response = _explain(client, review_session, run["id"], finding["id"])

    assert_problem(
        response, 409, "explanation-provenance-mismatch", detail_contains="requested run"
    )
    assert ai.calls == 0


def test_if_match_must_name_the_runs_model_version(client: TestClient, review_session: str) -> None:
    run = _review(client, review_session)
    finding_id = run["check_results"][0]["finding_ids"][0]

    stale = _explain(client, review_session, run["id"], finding_id, **{"If-Match": f'"{"0" * 64}"'})
    pinned = _explain(
        client, review_session, run["id"], finding_id, **{"If-Match": f'"{FIXTURE_SHA256}"'}
    )

    assert_problem(stale, 412, "model-version-mismatch", detail_contains=FIXTURE_SHA256)
    assert pinned.status_code == 200, pinned.text


def test_explanation_uses_the_runs_model_version_after_a_reupload(
    client: TestClient, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    replacement = FIXTURE_BYTES.replace(b"'Minimal Project'", b"'Replaced Project'")
    assert upload(client, review_session, replacement).status_code == 201
    active = hashlib.sha256(replacement).hexdigest()
    assert active != FIXTURE_SHA256

    against_active = _explain(
        client, review_session, run["id"], finding["id"], **{"If-Match": f'"{active}"'}
    )
    against_run = _explain(
        client, review_session, run["id"], finding["id"], **{"If-Match": f'"{FIXTURE_SHA256}"'}
    )

    assert_problem(against_active, 412, "model-version-mismatch")
    assert against_run.status_code == 200, against_run.text
    assert against_run.json()["citations"][0]["global_id"] == GLOBAL_IDS["W-002"]


def test_model_index_for_another_version_is_409(
    client: TestClient, settings: Settings, review_session: str
) -> None:
    run = _review(client, review_session)
    finding_id = run["check_results"][0]["finding_ids"][0]
    _rewrite_json(
        _index_path(settings, review_session),
        lambda payload: payload["summary"].update(model_hash="1" * 64),
    )

    response = _explain(client, review_session, run["id"], finding_id)

    assert_problem(response, 409, "explanation-provenance-mismatch", detail_contains="model")


def test_missing_model_index_is_409_not_a_storage_failure(
    client: TestClient, settings: Settings, review_session: str
) -> None:
    run = _review(client, review_session)
    finding_id = run["check_results"][0]["finding_ids"][0]
    _index_path(settings, review_session).unlink()

    response = _explain(client, review_session, run["id"], finding_id)

    assert_problem(response, 409, "explanation-provenance-mismatch", detail_contains="model")


def test_element_differing_from_the_runs_model_is_409(
    client: TestClient, settings: Settings, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    express_id = finding["elements"][0]["express_id"]

    def rename(payload: Any) -> None:
        for element in payload["elements"]:
            if element["ref"]["express_id"] == express_id:
                element["ref"]["name"] = "Renamed wall"

    _rewrite_json(_index_path(settings, review_session), rename)

    response = _explain(client, review_session, run["id"], finding["id"])

    assert_problem(response, 409, "explanation-provenance-mismatch", detail_contains="element")


def test_finding_moved_to_another_check_result_is_409(
    client: TestClient, settings: Settings, review_session: str
) -> None:
    run = _review(client, review_session)
    first, second = run["check_results"]

    def swap(payload: Any) -> None:
        a, b = payload["check_results"]
        a["finding_ids"], b["finding_ids"] = b["finding_ids"], a["finding_ids"]

    _rewrite_json(_run_dir(settings, review_session, run["id"]) / RUN_FILE, swap)

    response = _explain(client, review_session, run["id"], first["finding_ids"][0])

    assert second["finding_ids"] != first["finding_ids"]
    assert_problem(response, 409, "explanation-provenance-mismatch", detail_contains="check result")


def test_rule_version_outside_the_input_manifest_is_409(
    client: TestClient, settings: Settings, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])

    _rewrite_json(
        _run_dir(settings, review_session, run["id"]) / RUN_FILE,
        lambda payload: payload["input_manifest"]["rule_versions"].update(
            {finding["rule_id"]: "tampered"}
        ),
    )

    response = _explain(client, review_session, run["id"], finding["id"])

    assert_problem(response, 409, "explanation-provenance-mismatch", detail_contains="check")


def test_requirement_revision_changed_since_the_run_is_409(
    client: TestClient, store: SessionStore, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    _replace_requirement(store, review_session, "REQ-001", revision=2, confirmed_revision=2)

    response = _explain(client, review_session, run["id"], finding["id"])

    assert_problem(response, 409, "explanation-provenance-mismatch", detail_contains="revision")


def test_requirement_no_longer_confirmed_is_409(
    client: TestClient, store: SessionStore, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    _replace_requirement(
        store,
        review_session,
        "REQ-001",
        status="rejected",
        confirmed_revision=None,
        confirmed_by=None,
        confirmed_at=None,
    )

    response = _explain(client, review_session, run["id"], finding["id"])

    assert_problem(response, 409, "explanation-provenance-mismatch", detail_contains="confirmed")


def test_requirement_whose_check_changed_is_409(
    client: TestClient, store: SessionStore, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    current = next(item for item in store.read_requirements(review_session) if item.id == "REQ-001")
    assert current.check.ids_specification is not None
    altered = CheckSpec(
        kind=current.check.kind,
        rule_id=current.check.rule_id,
        rule_version=current.check.rule_version,
        ids_specification=current.check.ids_specification + " ",
    )
    assert altered.id != finding["check_id"]
    _replace_requirement(store, review_session, "REQ-001", check=altered.model_dump())

    response = _explain(client, review_session, run["id"], finding["id"])

    assert_problem(response, 409, "explanation-provenance-mismatch", detail_contains="check")


def test_requirement_source_outside_the_input_manifest_is_409(
    client: TestClient, store: SessionStore, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    current = next(item for item in store.read_requirements(review_session) if item.id == "REQ-001")
    assert current.source is not None
    foreign = RequirementSource(
        document_id="b" * 64, location=current.source.location, quote=current.source.quote
    )
    _replace_requirement(store, review_session, "REQ-001", source=foreign.model_dump())

    response = _explain(client, review_session, run["id"], finding["id"])

    assert_problem(response, 409, "explanation-provenance-mismatch", detail_contains="source")


def test_t5_missing_ids_source_is_rejected_before_explanation(
    client: TestClient, store: SessionStore, review_session: str
) -> None:
    run = _review(client, review_session)
    finding = _fire_finding(client, review_session, run["id"])
    _replace_requirement(store, review_session, "REQ-001", source=None)
    ai = FakeClient([_grounded(finding)])
    _use(client, lambda: ai)

    response = _explain(client, review_session, run["id"], finding["id"])

    assert_problem(response, 409, "explanation-provenance-mismatch", detail_contains="source")
    assert ai.calls == 0


def test_t5_builtin_requirement_does_not_need_a_document_source(
    client: TestClient, review_session: str, tmp_path: Path
) -> None:
    variant = write_variant(tmp_path, "typed-misclassification.ifc", add_misclassified_w002_type)
    assert upload(client, review_session, variant.read_bytes()).status_code == 201
    confirmed = client.post(
        f"{API_PREFIX}/sessions/{review_session}/requirements/native/classification-consistency"
    )
    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["source"] is None
    run = _review(client, review_session)
    finding = next(
        item for item in _findings(client, review_session, run["id"]) if item["method"] == "native"
    )
    assert finding["requirement_id"] == confirmed.json()["id"]

    response = _explain(client, review_session, run["id"], finding["id"])

    assert response.status_code == 200, response.text
    assert response.json()["finding_id"] == finding["id"]
    assert response.json()["fallback_reason"] == "ai_disabled"
