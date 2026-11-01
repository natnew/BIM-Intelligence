"""``POST /reviews``, ``GET /reviews/{runId}`` and ``GET /findings`` (FR-VAL-01, FR-VIS-02, AC-08).

The run is synchronous in this slice: the response body is the terminal ``ReviewRun``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import bim_intelligence.orchestration.planner as planner_module
from bim_intelligence.api.deps import get_llm_client
from bim_intelligence.api.main import API_PREFIX
from bim_intelligence.config import Settings
from bim_intelligence.llm.client import FakeClient
from bim_intelligence.store.session_store import RUNS_DIR
from fixtures.make_minimal_ifc import GLOBAL_IDS, SPEC_CLASSIFICATION, SPEC_FIRE_RATING
from support.api import FIXTURE_BYTES, assert_problem, upload
from support.ids import FIXTURE_IDS_BYTES, upload_ids
from support.llm_stub import CapturingCompletions, live_settings, stub_live_client

FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()
PLANNER_PROMPT = Path(planner_module.__file__).with_name("prompts") / "planner.v1.md"


@pytest.fixture
def review_session(client: TestClient, loaded_session: str) -> str:
    assert upload_ids(client, loaded_session, FIXTURE_IDS_BYTES).status_code == 201
    return loaded_session


def _start(client: TestClient, session_id: str, **headers: str) -> Any:
    return client.post(f"{API_PREFIX}/sessions/{session_id}/reviews", headers=headers)


def test_review_run_executes_both_checks_and_links_to_itself(
    client: TestClient, review_session: str
) -> None:
    response = _start(client, review_session)
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["status"] == "completed"
    assert run["plan_source"] == "default"
    assert run["session_id"] == review_session
    assert run["input_manifest"]["model_hash"] == FIXTURE_SHA256
    assert run["input_manifest"]["ids_hashes"] == [hashlib.sha256(FIXTURE_IDS_BYTES).hexdigest()]
    assert run["input_manifest"]["requirement_revisions"] == {"REQ-001": 1, "REQ-002": 1}
    assert [r["status"] for r in run["check_results"]] == ["failed", "failed"]
    assert [len(r["finding_ids"]) for r in run["check_results"]] == [1, 1]
    assert response.headers["Location"].endswith(f"/sessions/{review_session}/reviews/{run['id']}")

    fetched = client.get(f"{API_PREFIX}/sessions/{review_session}/reviews/{run['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == run


def test_objective_uses_only_model_selected_confirmed_checks(
    client: TestClient, review_session: str
) -> None:
    check_id = client.get(f"{API_PREFIX}/sessions/{review_session}/requirements").json()[0][
        "check"
    ]["id"]
    cast(FastAPI, client.app).dependency_overrides[get_llm_client] = lambda: FakeClient(
        [{"checks": [{"check_id": check_id, "reason": "It directly supports the objective."}]}]
    )
    response = client.post(
        f"{API_PREFIX}/sessions/{review_session}/reviews",
        json={"objective": "Review classification quality"},
    )
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["plan_source"] == "llm"
    assert [item["check_id"] for item in run["plan"]["checks"]] == [check_id]
    assert len(run["check_results"]) == 2
    assert run["check_results"][0]["check_id"] == check_id
    assert run["check_results"][0]["status"] == "failed"
    assert run["check_results"][1]["status"] == "skipped"
    assert run["check_results"][1]["diagnostics"] == [
        "Not selected by the objective-specific review plan."
    ]
    assert run["status"] == "partial"


def _confirmed_check_ids(client: TestClient, session_id: str) -> dict[str, str]:
    requirements = client.get(f"{API_PREFIX}/sessions/{session_id}/requirements").json()
    return {item["id"]: item["check"]["id"] for item in requirements}


def test_objective_reaches_the_planner_in_the_provider_request_body(
    client: TestClient, review_session: str, tmp_path: Path
) -> None:
    checks = _confirmed_check_ids(client, review_session)
    plan = {"checks": [{"check_id": checks["REQ-002"], "reason": "Classification objective."}]}
    completions = CapturingCompletions(json.dumps(plan))
    settings = live_settings(tmp_path)
    cast(FastAPI, client.app).dependency_overrides[get_llm_client] = lambda: stub_live_client(
        settings, completions
    )
    objective = "Review classification quality before the coordination meeting"

    response = client.post(
        f"{API_PREFIX}/sessions/{review_session}/reviews", json={"objective": objective}
    )

    assert response.status_code == 201, response.text
    run = response.json()
    assert run["plan_source"] == "llm"
    assert [item["check_id"] for item in run["plan"]["checks"]] == [checks["REQ-002"]]
    assert run["check_results"][0]["check_id"] == checks["REQ-002"]
    assert len(completions.requests) == 1
    request = completions.requests[0]
    assert request["model"] == "muse-spark-1.3"
    assert request["response_format"] == {"type": "json_object"}
    assert request["max_tokens"] == settings.llm_max_output_tokens_per_call
    system, user = request["messages"]
    assert system == {"role": "system", "content": PLANNER_PROMPT.read_text(encoding="utf-8")}
    assert user["role"] == "user"
    payload = json.loads(user["content"])
    assert payload["objective"] == objective
    assert payload["model_summary"]["model_hash"] == FIXTURE_SHA256
    assert sorted(item["check_id"] for item in payload["confirmed_requirements"]) == sorted(
        checks.values()
    )
    assert sorted(item["check_id"] for item in payload["available_checks"]) == sorted(
        checks.values()
    )


def test_planner_budget_rejection_runs_the_default_plan_without_a_provider_request(
    client: TestClient, review_session: str, tmp_path: Path
) -> None:
    checks = _confirmed_check_ids(client, review_session)
    completions = CapturingCompletions(
        json.dumps({"checks": [{"check_id": checks["REQ-001"], "reason": "Fire."}]})
    )
    tiny = "0.00001"
    settings = live_settings(
        tmp_path,
        llm_project_budget_usd=tiny,
        llm_max_run_budget_usd=tiny,
        llm_max_call_budget_usd=tiny,
    )
    cast(FastAPI, client.app).dependency_overrides[get_llm_client] = lambda: stub_live_client(
        settings, completions
    )

    response = client.post(
        f"{API_PREFIX}/sessions/{review_session}/reviews",
        json={"objective": "Check fire ratings only"},
    )

    assert response.status_code == 201, response.text
    run = response.json()
    assert run["plan_source"] == "default"
    assert [result["status"] for result in run["check_results"]] == ["failed", "failed"]
    assert completions.requests == []


def test_planner_request_failure_runs_the_default_plan(
    client: TestClient, review_session: str
) -> None:
    cast(FastAPI, client.app).dependency_overrides[get_llm_client] = lambda: FakeClient([])

    response = client.post(
        f"{API_PREFIX}/sessions/{review_session}/reviews",
        json={"objective": "Check fire ratings only"},
    )

    assert response.status_code == 201, response.text
    run = response.json()
    assert run["plan_source"] == "default"
    assert [result["status"] for result in run["check_results"]] == ["failed", "failed"]


@pytest.mark.parametrize("objective", ["", "   ", "\n\t"])
def test_blank_objective_is_rejected_before_planning(
    client: TestClient, settings: Settings, review_session: str, objective: str
) -> None:
    fake = FakeClient([{"checks": []}])
    cast(FastAPI, client.app).dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(
        f"{API_PREFIX}/sessions/{review_session}/reviews", json={"objective": objective}
    )

    assert_problem(response, 422, "request-validation", detail_contains="objective")
    assert fake.calls == 0
    runs_dir = settings.data_dir / "sessions" / review_session / RUNS_DIR
    assert not runs_dir.exists() or not any(runs_dir.iterdir())


def test_invalid_objective_plan_falls_back_to_deterministic_default(
    client: TestClient, review_session: str
) -> None:
    cast(FastAPI, client.app).dependency_overrides[get_llm_client] = lambda: FakeClient(
        [{"checks": [{"check_id": "unconfirmed", "reason": "Not registered."}]}]
    )
    response = client.post(
        f"{API_PREFIX}/sessions/{review_session}/reviews",
        json={"objective": "Review only the unconfirmed check"},
    )
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["plan_source"] == "default"
    assert len(run["plan"]["checks"]) == 2
    assert [result["status"] for result in run["check_results"]] == ["failed", "failed"]


def test_findings_expose_the_two_fixture_defects_with_evidence(
    client: TestClient, review_session: str
) -> None:
    run = _start(client, review_session).json()
    response = client.get(
        f"{API_PREFIX}/sessions/{review_session}/findings", params={"run_id": run["id"]}
    )
    assert response.status_code == 200, response.text
    findings = response.json()
    assert len(findings) == 2
    by_global_id = {f["elements"][0]["global_id"]: f for f in findings}
    assert set(by_global_id) == {GLOBAL_IDS["W-002"], GLOBAL_IDS["W-003"]}

    fire = by_global_id[GLOBAL_IDS["W-002"]]
    assert fire["method"] == "ids"
    assert fire["requirement_id"] == "REQ-001"
    assert fire["rule_id"] == f"ids:{SPEC_FIRE_RATING}"
    assert fire["category"] == "property_requirement"
    assert fire["observed"] == "The property set does not contain the required property"
    assert fire["expected"] == "FireRating data shall be provided in the dataset Pset_WallCommon"
    assert fire["elements"][0] == {
        "global_id": GLOBAL_IDS["W-002"],
        "express_id": 59,
        "ifc_type": "IfcWall",
        "name": "W-002",
        "storey": "L00",
    }

    classification = by_global_id[GLOBAL_IDS["W-003"]]
    assert classification["requirement_id"] == "REQ-002"
    assert classification["rule_id"] == f"ids:{SPEC_CLASSIFICATION}"
    assert classification["category"] == "classification_requirement"
    assert classification["observed"] == "The entity has no classification"

    assert sorted(f["id"] for f in findings) == sorted(
        fid for r in run["check_results"] for fid in r["finding_ids"]
    )
    # Every finding's element resolves through the element API of the same model version.
    for finding in findings:
        element = client.get(
            f"{API_PREFIX}/sessions/{review_session}/elements/{finding['elements'][0]['global_id']}",
            headers={"If-Match": f'"{FIXTURE_SHA256}"'},
        )
        assert element.status_code == 200
        assert element.json()["ref"] == finding["elements"][0]


def test_findings_can_be_filtered(client: TestClient, review_session: str) -> None:
    run_id = _start(client, review_session).json()["id"]
    base = f"{API_PREFIX}/sessions/{review_session}/findings"
    by_rule = client.get(base, params={"run_id": run_id, "rule_id": f"ids:{SPEC_FIRE_RATING}"})
    assert [f["elements"][0]["name"] for f in by_rule.json()] == ["W-002"]
    by_storey = client.get(base, params={"run_id": run_id, "storey": "L00"})
    assert len(by_storey.json()) == 2
    none = client.get(base, params={"run_id": run_id, "storey": "L01"})
    assert none.json() == []
    by_severity = client.get(base, params={"run_id": run_id, "severity": "info"})
    assert by_severity.json() == []
    bad_severity = client.get(base, params={"run_id": run_id, "severity": "fatal"})
    assert_problem(bad_severity, 422, "request-validation")


def test_explanation_is_separate_from_deterministic_findings(
    client: TestClient, review_session: str
) -> None:
    run = _start(client, review_session).json()
    base = f"{API_PREFIX}/sessions/{review_session}"
    findings = client.get(f"{base}/findings", params={"run_id": run["id"]}).json()
    finding = findings[0]
    element = finding["elements"][0]
    cast(FastAPI, client.app).dependency_overrides[get_llm_client] = lambda: FakeClient(
        [
            {
                "finding_id": finding["id"],
                "summary": (
                    f"{finding['observed']}; the verified check expected {finding['expected']}."
                ),
                "probable_cause": "The deterministic check found a mismatch.",
                "corrective_action": "Review the cited requirement and model element.",
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
        ]
    )
    response = client.post(f"{base}/reviews/{run['id']}/findings/{finding['id']}/explanation")
    assert response.status_code == 200, response.text
    explanation = response.json()
    assert explanation["source"] == "ai_generated"
    assert explanation["grounding_status"] == "passed"
    assert explanation["fallback_reason"] is None
    assert explanation["model"] == "fake-model"
    assert explanation["finding_id"] == finding["id"]
    assert explanation["citations"][0]["global_id"] == element["global_id"]
    assert client.get(f"{base}/findings", params={"run_id": run["id"]}).json() == findings


def test_findings_require_a_run_id(client: TestClient, review_session: str) -> None:
    response = client.get(f"{API_PREFIX}/sessions/{review_session}/findings")
    assert_problem(response, 422, "request-validation", detail_contains="run_id")


def test_two_runs_are_byte_identical_in_findings(client: TestClient, review_session: str) -> None:
    first = _start(client, review_session).json()
    second = _start(client, review_session).json()
    assert first["id"] != second["id"]
    base = f"{API_PREFIX}/sessions/{review_session}/findings"
    first_findings = client.get(base, params={"run_id": first["id"]}).content
    second_findings = client.get(base, params={"run_id": second["id"]}).content
    assert first_findings == second_findings
    for key in ("id", "created_at", "finished_at"):
        first.pop(key), second.pop(key)
    assert first == second


def test_review_honours_if_match(client: TestClient, review_session: str) -> None:
    stale = _start(client, review_session, **{"If-Match": '"' + "0" * 64 + '"'})
    assert_problem(stale, 412, "model-version-mismatch", detail_contains=FIXTURE_SHA256)
    pinned = _start(client, review_session, **{"If-Match": f'"{FIXTURE_SHA256}"'})
    assert pinned.status_code == 201


def test_review_without_a_model_is_404(client: TestClient, session_id: str) -> None:
    upload_ids(client, session_id, FIXTURE_IDS_BYTES)
    assert_problem(_start(client, session_id), 404, "model-not-found")


def test_review_without_requirements_is_409(client: TestClient, loaded_session: str) -> None:
    response = _start(client, loaded_session)
    assert_problem(response, 409, "no-executable-checks", detail_contains="confirmed")


def test_model_bytes_and_etag_are_unchanged_by_a_run(
    client: TestClient, review_session: str
) -> None:
    _start(client, review_session)
    file = client.get(f"{API_PREFIX}/sessions/{review_session}/model/file")
    assert file.content == FIXTURE_BYTES
    assert file.headers["ETag"] == f'"{FIXTURE_SHA256}"'


def test_reupload_after_a_run_does_not_rewrite_the_run(
    client: TestClient, review_session: str
) -> None:
    run = _start(client, review_session).json()
    replacement = FIXTURE_BYTES.replace(b"'Minimal Project'", b"'Replaced Project'")
    assert upload(client, review_session, replacement).status_code == 201
    fetched = client.get(f"{API_PREFIX}/sessions/{review_session}/reviews/{run['id']}").json()
    assert fetched == run
    assert fetched["input_manifest"]["model_hash"] == FIXTURE_SHA256


def test_unknown_run_is_404_and_malformed_run_id_is_400(
    client: TestClient, review_session: str
) -> None:
    base = f"{API_PREFIX}/sessions/{review_session}"
    assert_problem(
        client.get(f"{base}/reviews/6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b"), 404, "run-not-found"
    )
    assert_problem(client.get(f"{base}/reviews/not-a-run"), 400, "invalid-run-id")
    assert_problem(
        client.get(f"{base}/findings", params={"run_id": "6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b"}),
        404,
        "run-not-found",
    )
    assert_problem(client.get(f"{base}/findings", params={"run_id": "../x"}), 400, "invalid-run-id")
