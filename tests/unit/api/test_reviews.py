"""``POST /reviews``, ``GET /reviews/{runId}`` and ``GET /findings`` (FR-VAL-01, FR-VIS-02, AC-08).

The run is synchronous in this slice: the response body is the terminal ``ReviewRun``.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest
from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX
from fixtures.make_minimal_ifc import GLOBAL_IDS, SPEC_CLASSIFICATION, SPEC_FIRE_RATING
from support.api import FIXTURE_BYTES, assert_problem, upload
from support.ids import FIXTURE_IDS_BYTES, upload_ids

FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()


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
