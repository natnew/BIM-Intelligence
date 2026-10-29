"""End-to-end deterministic review, including the version-pinned viewer API contract."""

from __future__ import annotations

import hashlib
import socket
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX
from bim_intelligence.config import LLMMode, Settings
from fixtures.make_minimal_ifc import GLOBAL_IDS
from fixtures.variants import add_misclassified_w002_type, write_variant
from support.api import assert_problem, upload
from support.ids import FIXTURE_IDS_BYTES, upload_ids


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Make any attempted provider/external request fail while preserving TestClient loopback."""
    connect = socket.socket.connect
    connect_ex = socket.socket.connect_ex

    def check_address(address: Any) -> bool:
        return (
            isinstance(address, tuple)
            and bool(address)
            and address[0]
            in {
                "127.0.0.1",
                "::1",
                "localhost",
            }
        )

    def refuse_remote(self: socket.socket, address: Any) -> None:
        if not check_address(address):
            raise AssertionError(f"network access attempted: {address}")
        connect(self, address)

    def refuse_remote_ex(self: socket.socket, address: Any) -> int:
        if not check_address(address):
            raise AssertionError(f"network access attempted: {address}")
        return connect_ex(self, address)

    monkeypatch.setattr(socket.socket, "connect", refuse_remote)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse_remote_ex)
    yield


def test_fresh_session_runs_confirmed_ids_and_native_checks_without_llm(
    client: TestClient,
    settings: Settings,
    tmp_path: Path,
    no_network: None,
) -> None:
    assert settings.llm_mode is LLMMode.OFF
    session_response = client.post(f"{API_PREFIX}/sessions")
    assert session_response.status_code == 201, session_response.text
    session_id = session_response.json()["id"]

    variant_path = write_variant(
        tmp_path, "typed-misclassification.ifc", add_misclassified_w002_type
    )
    model_bytes = variant_path.read_bytes()
    model_hash = hashlib.sha256(model_bytes).hexdigest()
    assert upload(client, session_id, model_bytes).status_code == 201
    imported = upload_ids(client, session_id, FIXTURE_IDS_BYTES)
    assert imported.status_code == 201, imported.text
    requirements = client.get(f"{API_PREFIX}/sessions/{session_id}/requirements").json()
    assert len(requirements) == 2
    assert all(item["status"] == "confirmed" for item in requirements)

    native_path = (
        f"{API_PREFIX}/sessions/{session_id}/requirements/native/classification-consistency"
    )
    native_requirement = client.post(native_path)
    assert native_requirement.status_code == 201, native_requirement.text
    native_requirement_data = native_requirement.json()

    first_response = client.post(f"{API_PREFIX}/sessions/{session_id}/reviews")
    assert first_response.status_code == 201, first_response.text
    first_run = first_response.json()
    assert first_run["status"] == "completed"
    assert first_run["plan_source"] == "default"
    assert first_run["input_manifest"]["model_hash"] == model_hash
    assert first_run["input_manifest"]["ids_hashes"] == [
        hashlib.sha256(FIXTURE_IDS_BYTES).hexdigest()
    ]
    confirmed_requirements = [*requirements, native_requirement_data]
    assert first_run["input_manifest"]["requirement_revisions"] == {
        item["id"]: item["revision"] for item in confirmed_requirements
    }
    assert first_run["input_manifest"]["rule_versions"] == {
        item["check"]["rule_id"]: item["check"]["rule_version"] for item in confirmed_requirements
    }
    assert [result["requirement_id"] for result in first_run["check_results"]] == [
        item["id"] for item in confirmed_requirements
    ]
    assert len(first_run["plan"]["checks"]) == 3
    assert [result["status"] for result in first_run["check_results"]] == [
        "failed",
        "failed",
        "failed",
    ]

    findings_path = f"{API_PREFIX}/sessions/{session_id}/findings"
    first_findings_response = client.get(findings_path, params={"run_id": first_run["id"]})
    assert first_findings_response.status_code == 200
    first_findings = first_findings_response.json()
    assert len(first_findings) == 3
    by_rule_and_global_id = {
        (finding["rule_id"], finding["elements"][0]["global_id"]): finding
        for finding in first_findings
    }
    assert ("ids:External walls carry a fire rating", GLOBAL_IDS["W-002"]) in by_rule_and_global_id
    assert (
        "ids:Walls carry a classification reference",
        GLOBAL_IDS["W-003"],
    ) in by_rule_and_global_id
    native_finding = next(finding for finding in first_findings if finding["method"] == "native")
    assert native_finding["elements"][0]["global_id"] == GLOBAL_IDS["W-002"]
    assert GLOBAL_IDS["W-001"] not in {
        element["global_id"] for finding in first_findings for element in finding["elements"]
    }

    summary = client.get(f"{API_PREFIX}/sessions/{session_id}/model/summary")
    etag = summary.headers["ETag"]
    for finding in first_findings:
        element_ref = finding["elements"][0]
        element = client.get(
            f"{API_PREFIX}/sessions/{session_id}/elements/{element_ref['global_id']}",
            headers={"If-Match": etag},
        )
        assert element.status_code == 200
        assert element.json()["ref"] == element_ref
    model_file = client.get(
        f"{API_PREFIX}/sessions/{session_id}/model/file", headers={"If-Match": etag}
    )
    assert model_file.content == model_bytes
    assert model_file.headers["ETag"] == etag

    second_run = client.post(f"{API_PREFIX}/sessions/{session_id}/reviews").json()
    second_findings_response = client.get(findings_path, params={"run_id": second_run["id"]})
    assert second_findings_response.content == first_findings_response.content
    assert second_run["input_manifest"] == first_run["input_manifest"]
    assert second_run["check_results"] == first_run["check_results"]

    unknown = client.get(findings_path, params={"run_id": "6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b"})
    assert_problem(unknown, 404, "run-not-found")
