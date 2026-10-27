"""Health endpoint: liveness without secret exposure (ARCHITECTURE.md §11, AGENTS.md §8)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from bim_intelligence import __version__
from bim_intelligence.api.main import API_PREFIX, create_app
from bim_intelligence.config import Settings

PLACEHOLDER_KEY = "LLM_0_" + "x" * 24  # low-entropy stand-in; never a real key


def _client(**overrides: object) -> TestClient:
    return TestClient(create_app(Settings(**overrides)))  # type: ignore[arg-type]


def test_health_ok_with_defaults() -> None:
    response = _client().get(f"{API_PREFIX}/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["llm_mode"] == "off"
    assert body["llm_configured"] is False
    assert set(body["libraries"]) == {"ifcopenshell", "ifctester"}


def test_health_reports_key_presence_but_never_value() -> None:
    response = _client(model_api_key=PLACEHOLDER_KEY, llm_mode="live").get(f"{API_PREFIX}/health")
    assert response.status_code == 200
    assert response.json()["llm_configured"] is True
    assert PLACEHOLDER_KEY not in response.text
    assert "x" * 24 not in response.text


def test_openapi_served_under_versioned_prefix() -> None:
    response = _client().get(f"{API_PREFIX}/openapi.json")
    assert response.status_code == 200
    assert f"{API_PREFIX}/health" in response.json()["paths"]


def test_create_app_uses_the_settings_it_is_given() -> None:
    """Regression: routers must see the injected Settings, not the cached process defaults."""
    response = _client(llm_model="muse-wonder-1.0", llm_mode="replay").get(f"{API_PREFIX}/health")
    body = response.json()
    assert body["llm_model"] == "muse-wonder-1.0"
    assert body["llm_mode"] == "replay"
