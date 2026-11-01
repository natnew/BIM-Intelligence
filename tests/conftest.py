"""Shared fixtures. No test may read a developer's real ``.env`` or make network calls.

The only exception is a test marked ``live``: it exists to exercise the owner's configured Meta
access and carries its own marker, environment and approval-token gates (C-06).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from bim_intelligence.config import Settings, get_settings

pytest_plugins = ("support.api_fixtures", "pytester")

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
def _isolated_environment(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Strip BIMI variables and disable ``.env`` loading so tests are hermetic.

    ``live`` tests keep the real configuration; isolating them would make the owner-approved
    smoke test unreachable, because it could never see ``LLM_MODE`` or ``MODEL_API_KEY``.
    """
    if request.node.get_closest_marker("live") is None:
        for name in ENV_VARS:
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
