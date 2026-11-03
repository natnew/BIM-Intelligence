"""The exported JSON Schema bundle is the frontend contract (ADR-014, C-07, W-17).

``frontend/src/api/generated/bim_intelligence.schema.json`` is committed; this test fails when the
Pydantic models change without re-running ``python scripts/export_schemas.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bim_intelligence.schemas import (
    CONTRACT_MODELS,
    ReviewProvenance,
    build_contract_schema,
    contract_schema_json,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "frontend" / "src" / "api" / "generated" / "bim_intelligence.schema.json"
EXPECTED_NAMES = {
    "Session",
    "ElementRef",
    "PropertyValue",
    "ClassificationRef",
    "ElementRecord",
    "ModelSummary",
    "CheckSpec",
    "RequirementSource",
    "Requirement",
    "Finding",
    "CheckResult",
    "PlannedCheck",
    "ReviewPlan",
    "ReviewProvenance",
    "InputManifest",
    "ReviewRun",
    "ProblemDetail",
    "AIReviewFailure",
    "DocumentImport",
    "RequirementCandidate",
    "RequirementCandidateBatch",
    "RequirementCandidateConfirmation",
    "RequirementExtractionRequest",
    "ReviewRequest",
    "SelectedCheck",
    "Explanation",
    "EvidenceCitation",
    "BudgetStatus",
}


def test_bundle_defines_every_contract_model() -> None:
    bundle = build_contract_schema()
    assert set(bundle["$defs"]) >= EXPECTED_NAMES
    assert {model.__name__ for model in CONTRACT_MODELS} == EXPECTED_NAMES


def test_every_object_schema_is_closed() -> None:
    bundle = build_contract_schema()
    for name, definition in bundle["$defs"].items():
        if definition.get("type") == "object" and "properties" in definition:
            assert definition.get("additionalProperties") is False, name


def test_derived_identifiers_are_required_in_the_serialised_contract() -> None:
    defs = build_contract_schema()["$defs"]
    assert "id" in defs["Finding"]["required"]
    assert "id" in defs["CheckSpec"]["required"]
    assert set(defs["Finding"]["properties"]["method"]["enum"]) == {"ids", "native"}
    assert "created_at" not in defs["Finding"]["properties"]


def test_bundle_is_deterministic() -> None:
    assert contract_schema_json() == contract_schema_json()
    assert contract_schema_json().endswith("\n")


def test_committed_schema_matches_models() -> None:
    assert SCHEMA_PATH.exists(), "run: python scripts/export_schemas.py"
    committed = SCHEMA_PATH.read_text(encoding="utf-8")
    assert json.loads(committed) == build_contract_schema()
    assert committed == contract_schema_json(), "run: python scripts/export_schemas.py"


def test_review_provenance_rejects_a_provider_attempt_outside_live_mode() -> None:
    with pytest.raises(ValidationError, match="requires live mode"):
        ReviewProvenance(
            ai_planning_requested=True,
            provider_request_attempted=True,
            mode="replay",
            outcome="accepted",
        )


def test_review_provenance_requires_reason_for_deterministic_rejection() -> None:
    with pytest.raises(ValidationError, match="requires a reason"):
        ReviewProvenance(
            ai_planning_requested=True,
            provider_request_attempted=False,
            mode="off",
            outcome="rejected",
        )
