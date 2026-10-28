"""Error envelope and correlation ids (ARCHITECTURE §14, §15; AGENTS.md §8)."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX
from bim_intelligence.config import Settings
from bim_intelligence.schemas import ProblemDetail
from support.api import PROBLEM_JSON, assert_problem


def test_unknown_route_is_a_problem_detail(client: TestClient) -> None:
    response = client.get(f"{API_PREFIX}/nope")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM_JSON)
    body = response.json()
    assert body["title"] == "Not Found"
    assert body["type"] == "about:blank"
    ProblemDetail.model_validate(body)


def test_method_not_allowed_is_a_problem_detail(client: TestClient, session_id: str) -> None:
    response = client.delete(f"{API_PREFIX}/sessions/{session_id}")
    assert response.status_code == 405
    assert response.headers["content-type"].startswith(PROBLEM_JSON)
    assert response.json()["status"] == 405


def test_every_problem_validates_against_the_contract(client: TestClient) -> None:
    body = assert_problem(client.get(f"{API_PREFIX}/sessions/bad"), 400, "invalid-session-id")
    ProblemDetail.model_validate(body)


class TestCorrelationId:
    def test_generated_when_absent_on_success_and_failure(self, client: TestClient) -> None:
        ok = client.get(f"{API_PREFIX}/health")
        bad = client.get(f"{API_PREFIX}/sessions/bad")
        for response in (ok, bad):
            assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-correlation-id"])
        assert ok.headers["x-correlation-id"] != bad.headers["x-correlation-id"]

    def test_well_formed_client_id_is_echoed(self, client: TestClient) -> None:
        response = client.get(f"{API_PREFIX}/health", headers={"X-Correlation-ID": "req-42_a"})
        assert response.headers["x-correlation-id"] == "req-42_a"

    def test_unsafe_client_id_is_replaced(self, client: TestClient) -> None:
        bad = "x" * 65
        response = client.get(f"{API_PREFIX}/health", headers={"X-Correlation-ID": bad})
        assert response.headers["x-correlation-id"] != bad
        injected = client.get(f"{API_PREFIX}/health", headers={"X-Correlation-ID": "a b\tc"})
        assert injected.headers["x-correlation-id"] != "a b\tc"

    def test_problem_body_carries_the_same_id(self, client: TestClient) -> None:
        response = client.get(
            f"{API_PREFIX}/sessions/0f1b7a2e-5c3d-4e8f-9a1b-2c3d4e5f6a7b",
            headers={"X-Correlation-ID": "trace-1"},
        )
        body = assert_problem(response, 404, "session-not-found")
        assert body["correlation_id"] == "trace-1"


def test_storage_failure_is_500_without_internal_detail(
    client: TestClient, session_id: str, settings: Settings
) -> None:
    record = settings.data_dir / "sessions" / session_id / "session.json"
    record.write_text("{corrupt", encoding="utf-8")
    response = client.get(f"{API_PREFIX}/sessions/{session_id}")
    body = assert_problem(response, 500, "storage-failure")
    assert str(settings.data_dir) not in response.text
    assert "corrupt" not in str(body["detail"])


def test_cors_exposes_etag_and_correlation_headers(client: TestClient) -> None:
    response = client.get(f"{API_PREFIX}/health", headers={"Origin": "http://localhost:5173"})
    exposed = {
        h.strip().lower() for h in response.headers["access-control-expose-headers"].split(",")
    }
    assert {"etag", "x-correlation-id"} <= exposed
