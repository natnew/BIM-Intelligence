"""HTTP helpers shared by the API tests."""

from __future__ import annotations

from typing import cast

import httpx
from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX
from fixtures.make_minimal_ifc import IFC_PATH

FIXTURE_BYTES = IFC_PATH.read_bytes()
PROBLEM_JSON = "application/problem+json"


def upload(
    client: TestClient, session_id: str, data: bytes, filename: str = "minimal.ifc"
) -> httpx.Response:
    response = client.post(
        f"{API_PREFIX}/sessions/{session_id}/model",
        files={"file": (filename, data, "application/x-step")},
    )
    return cast(httpx.Response, response)


def assert_problem(
    response: httpx.Response, status: int, slug: str, *, detail_contains: str | None = None
) -> dict[str, object]:
    """Every error is an RFC 9457 body with our problem-type URI and a correlation id."""
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith(PROBLEM_JSON)
    body: dict[str, object] = response.json()
    assert body["status"] == status
    assert str(body["type"]).endswith(f"/problems/{slug}")
    assert body["title"]
    assert body["instance"] == response.request.url.path
    assert body["correlation_id"] == response.headers["x-correlation-id"]
    if detail_contains is not None:
        assert detail_contains in str(body["detail"])
    return body
