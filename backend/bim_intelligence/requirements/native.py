"""Explicit confirmation of registered native checks as built-in requirements."""

from __future__ import annotations

from dataclasses import dataclass

from bim_intelligence.schemas import Requirement
from bim_intelligence.store import SessionStore
from bim_intelligence.validation import (
    CLASSIFICATION_CONSISTENCY_STATEMENT,
    CLASSIFICATION_CONSISTENCY_TITLE,
    classification_consistency_check,
)

CONFIRMED_BY_NATIVE_SELECTION = "native-check-selection"


@dataclass(frozen=True)
class NativeRequirementResult:
    requirement: Requirement
    created: bool


def confirm_classification_consistency(
    store: SessionStore, session_id: str
) -> NativeRequirementResult:
    """Register the fixed P0 rule only after an explicit request; repeated calls are idempotent."""
    check = classification_consistency_check()
    with store.lock_model(session_id) as lock:
        requirements = store.read_requirements(session_id)
        existing = next((item for item in requirements if item.check.id == check.id), None)
        if existing is not None:
            return NativeRequirementResult(existing, created=False)

        requirement = Requirement(
            id=f"REQ-BUILTIN-{check.id}",
            title=CLASSIFICATION_CONSISTENCY_TITLE,
            statement=CLASSIFICATION_CONSISTENCY_STATEMENT,
            origin="builtin",
            check=check,
            status="confirmed",
            revision=1,
            confirmed_revision=1,
            confirmed_by=CONFIRMED_BY_NATIVE_SELECTION,
            confirmed_at=store.now(),
        )
        store.write_requirements(lock, [*requirements, requirement])
    return NativeRequirementResult(requirement, created=True)
