"""Shared fixtures. No test may read a developer's real ``.env`` or make network calls."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from bim_intelligence.config import Settings, get_settings

pytest_plugins = ("support.api_fixtures",)

ENV_VARS = (
    "MODEL_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_MODE",
    "ALLOW_CONTRIBUTOR_MODELS",
    "BIMI_HOST",
    "BIMI_PORT",
    "ALLOW_REMOTE",
    "CORS_ORIGINS",
    "DATA_DIR",
)


@pytest.fixture(autouse=True)
def _isolated_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip BIMI variables and disable ``.env`` loading so tests are hermetic."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
