"""Session endpoints (ARCHITECTURE §11): create, fetch, isolate; never expose paths."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX
from bim_intelligence.config import Settings
from bim_intelligence.schemas import SESSION_ID_PATTERN
from support.api import FIXTURE_BYTES, assert_problem, upload

UNKNOWN_ID = "0f1b7a2e-5c3d-4e8f-9a1b-2c3d4e5f6a7b"


def test_create_session_returns_201_with_a_location_header(
    client: TestClient, settings: Settings
) -> None:
    response = client.post(f"{API_PREFIX}/sessions")
    assert response.status_code == 201
    body = response.json()
    assert re.fullmatch(SESSION_ID_PATTERN, body["id"])
    assert body["status"] == "created"
    assert body["model_hash"] is None
    assert body["document_hashes"] == []
    assert response.headers["location"] == f"{API_PREFIX}/sessions/{body['id']}"
    assert set(body) == {"id", "created_at", "status", "model_hash", "document_hashes"}
    assert str(settings.data_dir) not in response.text


def test_get_session_round_trips(client: TestClient, session_id: str) -> None:
    created = client.get(f"{API_PREFIX}/sessions/{session_id}")
    assert created.status_code == 200
    assert created.json()["id"] == session_id
    assert created.json()["status"] == "created"


def test_session_reflects_the_uploaded_model(client: TestClient, loaded_session: str) -> None:
    body = client.get(f"{API_PREFIX}/sessions/{loaded_session}").json()
    assert body["status"] == "model_ready"
    assert re.fullmatch(r"[0-9a-f]{64}", body["model_hash"])


def test_unknown_session_is_404_problem(client: TestClient) -> None:
    response = client.get(f"{API_PREFIX}/sessions/{UNKNOWN_ID}")
    assert_problem(response, 404, "session-not-found", detail_contains=UNKNOWN_ID)


def test_malformed_session_id_is_400_problem(client: TestClient) -> None:
    response = client.get(f"{API_PREFIX}/sessions/not-a-session")
    assert_problem(response, 400, "invalid-session-id")
    traversal = client.get(f"{API_PREFIX}/sessions/..%2F..%2Fetc")
    assert traversal.status_code in {400, 404}
    assert traversal.headers["content-type"].startswith("application/problem+json")


def test_sessions_are_isolated(client: TestClient) -> None:
    a = client.post(f"{API_PREFIX}/sessions").json()["id"]
    b = client.post(f"{API_PREFIX}/sessions").json()["id"]
    assert upload(client, a, FIXTURE_BYTES).status_code == 201
    assert client.get(f"{API_PREFIX}/sessions/{a}/model/summary").status_code == 200
    assert_problem(client.get(f"{API_PREFIX}/sessions/{b}/model/summary"), 404, "model-not-found")
    assert client.get(f"{API_PREFIX}/sessions/{b}").json()["status"] == "created"


def test_data_directory_is_created_lazily_under_data_dir(
    client: TestClient, settings: Settings
) -> None:
    assert not settings.data_dir.exists()
    session_id = client.post(f"{API_PREFIX}/sessions").json()["id"]
    assert (settings.data_dir / "sessions" / session_id / "session.json").is_file()
