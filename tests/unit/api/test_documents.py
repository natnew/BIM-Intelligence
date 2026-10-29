"""``POST /sessions/{sid}/documents`` and ``GET /sessions/{sid}/requirements`` (FR-REQ-05)."""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from bim_intelligence.api.deps import SESSIONS_DIR
from bim_intelligence.api.main import API_PREFIX
from bim_intelligence.config import Settings
from bim_intelligence.store import SessionStore
from fixtures.make_minimal_ifc import SPEC_CLASSIFICATION, SPEC_FIRE_RATING
from support.api import assert_problem
from support.ids import (
    FIXTURE_IDS_BYTES,
    MALFORMED_XML,
    SCHEMA_INVALID_IDS,
    ids_document,
    specification,
    upload_ids,
)


def test_valid_ids_upload_returns_the_confirmed_requirements(
    client: TestClient, session_id: str
) -> None:
    response = upload_ids(client, session_id, FIXTURE_IDS_BYTES)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["kind"] == "ids"
    assert body["sha256"] == hashlib.sha256(FIXTURE_IDS_BYTES).hexdigest()
    assert body["title"] == "BIM Intelligence minimal fixture"
    assert [r["id"] for r in body["requirements"]] == ["REQ-001", "REQ-002"]
    assert [r["title"] for r in body["requirements"]] == [SPEC_FIRE_RATING, SPEC_CLASSIFICATION]
    assert all(r["status"] == "confirmed" for r in body["requirements"])
    assert all(r["check"]["kind"] == "ids" for r in body["requirements"])
    assert all(r["check"]["ids_specification"] for r in body["requirements"])
    assert response.headers["Location"].endswith(f"/sessions/{session_id}/requirements")

    session = client.get(f"{API_PREFIX}/sessions/{session_id}").json()
    assert session["document_hashes"] == [body["sha256"]]


def test_reuploading_the_same_ids_is_idempotent(client: TestClient, session_id: str) -> None:
    first = upload_ids(client, session_id, FIXTURE_IDS_BYTES)
    second = upload_ids(client, session_id, FIXTURE_IDS_BYTES)
    assert first.status_code == 201 and second.status_code == 200
    assert first.json() == second.json()
    listed = client.get(f"{API_PREFIX}/sessions/{session_id}/requirements").json()
    assert len(listed) == 2


@pytest.mark.parametrize(
    ("data", "detail"),
    [(MALFORMED_XML, "well-formed"), (SCHEMA_INVALID_IDS, "IDS 1.0")],
    ids=["malformed", "xsd-invalid"],
)
def test_invalid_ids_is_422_problem(
    client: TestClient, session_id: str, data: bytes, detail: str
) -> None:
    response = upload_ids(client, session_id, data)
    assert_problem(response, 422, "ids-invalid", detail_contains=detail)
    assert client.get(f"{API_PREFIX}/sessions/{session_id}/requirements").json() == []


@pytest.mark.parametrize("filename", ["requirements.txt", "model.ifc", "bep.pdf", "ids"])
def test_only_ids_documents_are_accepted_in_this_slice(
    client: TestClient, session_id: str, filename: str
) -> None:
    response = upload_ids(client, session_id, FIXTURE_IDS_BYTES, filename=filename)
    assert_problem(response, 415, "unsupported-upload", detail_contains=".ids")


def test_oversized_document_is_413(client: TestClient, session_id: str) -> None:
    padding = specification(
        "Padded", "<entity><name><simpleValue>IFCWALL</simpleValue></name></entity>"
    )
    bloated = ids_document(*([padding] * 6000))
    assert len(bloated) > 1 << 20
    response = upload_ids(client, session_id, bloated)
    assert_problem(response, 413, "upload-too-large")


def test_missing_file_field_is_422_request_validation(client: TestClient, session_id: str) -> None:
    response = client.post(f"{API_PREFIX}/sessions/{session_id}/documents")
    assert_problem(response, 422, "request-validation")


def test_documents_for_unknown_or_invalid_session(client: TestClient) -> None:
    assert_problem(
        upload_ids(client, "6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b", FIXTURE_IDS_BYTES),
        404,
        "session-not-found",
    )
    assert_problem(
        upload_ids(client, "not-a-session", FIXTURE_IDS_BYTES), 400, "invalid-session-id"
    )


def test_requirements_list_is_empty_until_a_document_is_imported(
    client: TestClient, session_id: str
) -> None:
    response = client.get(f"{API_PREFIX}/sessions/{session_id}/requirements")
    assert response.status_code == 200
    assert response.json() == []


def test_requirements_list_returns_every_imported_requirement(
    client: TestClient, session_id: str
) -> None:
    upload_ids(client, session_id, FIXTURE_IDS_BYTES)
    response = client.get(f"{API_PREFIX}/sessions/{session_id}/requirements")
    assert response.status_code == 200
    body = response.json()
    assert [r["id"] for r in body] == ["REQ-001", "REQ-002"]
    assert body[0]["source"]["document_id"] == hashlib.sha256(FIXTURE_IDS_BYTES).hexdigest()
    assert body[0]["source"]["quote"] == SPEC_FIRE_RATING


def test_requirements_for_unknown_session_is_404(client: TestClient) -> None:
    response = client.get(
        f"{API_PREFIX}/sessions/6f1c2b3a-4d5e-4f60-8a9b-0c1d2e3f4a5b/requirements"
    )
    assert_problem(response, 404, "session-not-found")


def test_document_upload_while_the_model_lock_is_held_is_409(
    client: TestClient, session_id: str, settings: Settings
) -> None:
    store = SessionStore(settings.data_dir / SESSIONS_DIR)
    with store.lock_model(session_id):
        response = upload_ids(client, session_id, FIXTURE_IDS_BYTES)
    assert_problem(response, 409, "model-locked")
