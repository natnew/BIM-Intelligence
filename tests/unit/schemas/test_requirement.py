"""Requirement lifecycle: confirmation is bound to a revision (ADR-008, FR-REQ-04, C-02)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from bim_intelligence.schemas import CheckSpec, Requirement, RequirementSource

CHECK = CheckSpec(kind="native", rule_id="classification.present", rule_version="1.0.0")


def make_requirement(**overrides: object) -> Requirement:
    data: dict[str, object] = {
        "id": "REQ-001",
        "title": "Walls are classified",
        "statement": "Every wall shall carry a classification reference.",
        "origin": "ids",
        "check": CHECK,
        "status": "confirmed",
        "revision": 1,
        "confirmed_revision": 1,
    }
    data.update(overrides)
    return Requirement.model_validate(data)


def test_confirmed_requirement_at_current_revision_is_executable() -> None:
    requirement = make_requirement()
    assert requirement.is_executable is True


@pytest.mark.parametrize("status", ["proposed", "edited", "rejected", "informational"])
def test_non_confirmed_statuses_are_never_executable(status: str) -> None:
    requirement = make_requirement(status=status, confirmed_revision=None)
    assert requirement.is_executable is False


def test_confirmed_status_requires_matching_confirmed_revision() -> None:
    with pytest.raises(ValidationError, match="confirmed_revision"):
        make_requirement(status="confirmed", confirmed_revision=None)
    with pytest.raises(ValidationError, match="confirmed_revision"):
        make_requirement(status="confirmed", revision=2, confirmed_revision=1)


def test_edit_after_confirmation_keeps_old_confirmed_revision_but_is_not_executable() -> None:
    edited = make_requirement(status="edited", revision=2, confirmed_revision=1)
    assert edited.is_executable is False


def test_confirmed_revision_cannot_exceed_revision() -> None:
    with pytest.raises(ValidationError):
        make_requirement(status="proposed", revision=1, confirmed_revision=2)


def test_document_origin_requires_verbatim_source() -> None:
    with pytest.raises(ValidationError, match="source"):
        make_requirement(origin="document", source=None)
    source = RequirementSource(document_id="bep-01", location="p-034", quote="All external walls…")
    assert make_requirement(origin="document", source=source).source == source


def test_confidence_is_bounded_and_optional() -> None:
    assert make_requirement(confidence=None).confidence is None
    assert make_requirement(confidence=0.82).confidence == 0.82
    with pytest.raises(ValidationError):
        make_requirement(confidence=1.5)


def test_confirmed_at_must_be_timezone_aware() -> None:
    aware = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
    assert make_requirement(confirmed_at=aware).confirmed_at == aware
    with pytest.raises(ValidationError):
        make_requirement(confirmed_at=datetime(2026, 10, 27, 12, 0))


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        make_requirement(params={"weaken": True})
