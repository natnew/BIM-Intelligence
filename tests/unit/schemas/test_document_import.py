"""DocumentImport: what ``POST /sessions/{sid}/documents`` returns (FR-REQ-05)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from bim_intelligence.schemas import CheckSpec, DocumentImport, Requirement

NOW = datetime(2026, 10, 29, tzinfo=timezone.utc)


def _requirement() -> Requirement:
    return Requirement(
        id="REQ-001",
        title="t",
        statement="s",
        origin="ids",
        check=CheckSpec(kind="ids", rule_id="ids:t", rule_version="v", ids_specification="<s/>"),
        status="confirmed",
        confirmed_revision=1,
        confirmed_by="ids-import",
        confirmed_at=NOW,
    )


def test_document_import_is_frozen_and_closed() -> None:
    document = DocumentImport(sha256="a" * 64, kind="ids", title="T", requirements=[_requirement()])
    with pytest.raises(ValidationError):
        document.title = "U"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        DocumentImport.model_validate({**document.model_dump(), "path": "/tmp/x"})


def test_document_import_requires_a_content_hash_and_a_known_kind() -> None:
    with pytest.raises(ValidationError):
        DocumentImport(sha256="not-a-hash", kind="ids", title="T", requirements=[])
    with pytest.raises(ValidationError):
        DocumentImport.model_validate(
            {"sha256": "a" * 64, "kind": "bep", "title": "T", "requirements": []}
        )
