"""API test fixtures: an app bound to a temporary data directory and a 1 MiB upload cap.

Registered from the root ``conftest.py`` via ``pytest_plugins`` so that no second module named
``conftest`` exists (mypy checks every test module under one namespace).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bim_intelligence.api.main import API_PREFIX, create_app
from bim_intelligence.config import Settings
from support.api import FIXTURE_BYTES, upload


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", max_ifc_mb=1)


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture
def session_id(client: TestClient) -> str:
    response = client.post(f"{API_PREFIX}/sessions")
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


@pytest.fixture
def loaded_session(client: TestClient, session_id: str) -> str:
    """A session whose model is the committed fixture."""
    response = upload(client, session_id, FIXTURE_BYTES)
    assert response.status_code == 201, response.text
    return session_id
