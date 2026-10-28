"""Session record: the directory-backed review context (ADR-006, ARCHITECTURE §10.2)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from bim_intelligence.schemas import SESSION_ID_PATTERN, Session

SESSION_ID = "0f1b7a2e-5c3d-4e8f-9a1b-2c3d4e5f6a7b"
CREATED_AT = datetime(2026, 10, 28, 9, 0, tzinfo=timezone.utc)


def test_session_id_is_a_lower_case_uuid4() -> None:
    session = Session(id=SESSION_ID, created_at=CREATED_AT, status="created")
    assert session.id == SESSION_ID
    assert session.model_hash is None
    assert session.document_hashes == []


@pytest.mark.parametrize(
    "bad_id",
    [
        "",
        "not-a-uuid",
        "0F1B7A2E-5C3D-4E8F-9A1B-2C3D4E5F6A7B",  # upper case
        "0f1b7a2e-5c3d-1e8f-9a1b-2c3d4e5f6a7b",  # version 1
        "../0f1b7a2e-5c3d-4e8f-9a1b-2c3d4e5f6a7b",
        "0f1b7a2e5c3d4e8f9a1b2c3d4e5f6a7b",  # unhyphenated
    ],
)
def test_malformed_ids_are_rejected(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        Session(id=bad_id, created_at=CREATED_AT, status="created")


def test_created_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        Session(id=SESSION_ID, created_at=datetime(2026, 10, 28, 9, 0), status="created")


def test_model_ready_requires_a_model_hash_and_vice_versa() -> None:
    ready = Session(id=SESSION_ID, created_at=CREATED_AT, status="model_ready", model_hash="a" * 64)
    assert ready.model_hash == "a" * 64
    with pytest.raises(ValidationError, match="model_hash"):
        Session(id=SESSION_ID, created_at=CREATED_AT, status="model_ready")
    with pytest.raises(ValidationError, match="model_hash"):
        Session(id=SESSION_ID, created_at=CREATED_AT, status="created", model_hash="a" * 64)


def test_unknown_fields_and_unknown_status_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Session(id=SESSION_ID, created_at=CREATED_AT, status="running")
    with pytest.raises(ValidationError):
        Session(id=SESSION_ID, created_at=CREATED_AT, status="created", path="/tmp/x")  # type: ignore[call-arg]


def test_pattern_is_exported_for_path_validation() -> None:
    import re

    assert re.fullmatch(SESSION_ID_PATTERN, SESSION_ID)
    assert not re.fullmatch(SESSION_ID_PATTERN, "..")
