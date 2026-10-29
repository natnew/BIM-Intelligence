"""CORS preflight: the version preconditions must be usable from the browser (ADR-017 §3).

``If-Match`` and ``If-None-Match`` are not CORS-safelisted request headers, so a frontend on
another origin can only send them if the preflight response lists them. Regression test for
the T-2 correction of the allow-list.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX, create_app
from bim_intelligence.config import Settings

ORIGIN = "http://localhost:5173"


@pytest.fixture
def cors_client(settings: Settings) -> TestClient:
    assert ORIGIN in settings.cors_origins
    return TestClient(create_app(settings))


def _preflight(client: TestClient, path: str, method: str, headers: str) -> dict[str, str]:
    response = client.options(
        f"{API_PREFIX}{path}",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )
    assert response.status_code == 200, response.text
    return {k.lower(): v for k, v in response.headers.items()}


@pytest.mark.parametrize(
    ("path", "method", "header"),
    [
        ("/sessions/x/model/summary", "GET", "if-match"),
        ("/sessions/x/model/file", "GET", "if-none-match"),
        ("/sessions/x/elements/y", "GET", "if-match"),
        ("/sessions/x/reviews", "POST", "if-match"),
    ],
)
def test_preflight_permits_the_version_precondition_headers(
    cors_client: TestClient, path: str, method: str, header: str
) -> None:
    headers = _preflight(cors_client, path, method, f"{header}, x-correlation-id")
    allowed = {h.strip().lower() for h in headers["access-control-allow-headers"].split(",")}
    assert header in allowed
    assert "x-correlation-id" in allowed
    assert headers["access-control-allow-origin"] == ORIGIN


def test_preflight_exposes_the_etag_to_scripts(cors_client: TestClient) -> None:
    response = cors_client.get(f"{API_PREFIX}/health", headers={"Origin": ORIGIN})
    assert response.status_code == 200
    exposed = {
        h.strip().lower() for h in response.headers["access-control-expose-headers"].split(",")
    }
    assert {"etag", "x-correlation-id"} <= exposed
