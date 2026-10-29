from __future__ import annotations

from bim_intelligence.bim import ModelIndex
from bim_intelligence.llm.client import FakeClient
from bim_intelligence.reporting.explanations import explain_finding
from bim_intelligence.schemas import (
    CheckSpec,
    ElementRecord,
    ElementRef,
    EvidenceCitation,
    Finding,
    ModelSummary,
    PropertyValue,
    Requirement,
    RequirementSource,
)
from fixtures.make_minimal_ifc import GLOBAL_IDS


def _models() -> tuple[Finding, Requirement, ModelIndex]:
    reference = ElementRef(
        global_id=GLOBAL_IDS["W-002"],
        express_id=1,
        ifc_type="IfcWall",
        name="W-002",
        storey="L00",
    )
    check = CheckSpec(
        kind="native",
        rule_id="test.fire_rating",
        rule_version="1.0.0",
        params={},
    )
    finding = Finding(
        check_id=check.id,
        requirement_id="REQ-001",
        rule_id=check.rule_id,
        rule_version=check.rule_version,
        facet_index=0,
        severity="error",
        category="property_requirement",
        elements=[reference],
        observed="W-002 has FireRating 'TBC'.",
        expected="FireRating must be 'REI 60'.",
        method="native",
    )
    requirement = Requirement(
        id="REQ-001",
        title="Wall fire rating",
        statement="Every wall must have a fire rating.",
        origin="document",
        source=RequirementSource(
            document_id="a" * 64,
            location="p-001",
            quote="Every wall must have a fire rating.",
        ),
        check=check,
        status="confirmed",
        revision=1,
        confirmed_revision=1,
    )
    record = ElementRecord(
        ref=reference,
        psets={"Pset_WallCommon": {"FireRating": PropertyValue(value="TBC", inherited=False)}},
        classifications=[],
    )
    index = ModelIndex(
        summary=ModelSummary(
            ifc_schema="IFC4",
            model_hash="0" * 64,
            counts={"IfcWall": 1},
            storeys=[],
        ),
        elements=[record],
    )
    return finding, requirement, index


def test_invalid_or_mixed_evidence_uses_deterministic_fallback() -> None:
    finding, requirement, index = _models()
    result = explain_finding(
        finding,
        requirement,
        index,
        FakeClient(
            [
                {
                    "finding_id": finding.id,
                    "summary": "GlobalId 0000000000000000000000 has 90 mm.",
                    "probable_cause": "FireRating is wrong.",
                    "corrective_action": "Set it to 90 mm.",
                    "citations": [],
                }
            ]
        ),
        run_id="run-1",
    )
    assert result.source == "deterministic_template"
    assert result.grounding_status == "fallback"


def test_valid_grounded_explanation_is_labelled_ai_generated() -> None:
    finding, requirement, index = _models()
    element = finding.elements[0]
    citation = {
        "finding_id": finding.id,
        "global_id": element.global_id,
        "requirement_id": finding.requirement_id,
        "rule_id": finding.rule_id,
        "expected": finding.expected,
        "observed": finding.observed,
    }
    result = explain_finding(
        finding,
        requirement,
        index,
        FakeClient(
            [
                {
                    "finding_id": finding.id,
                    "summary": "W-002 has FireRating 'TBC'; the requirement expects 'REI 60'.",
                    "probable_cause": "The recorded value is TBC.",
                    "corrective_action": "Replace TBC with REI 60.",
                    "citations": [citation],
                }
            ]
        ),
        run_id="run-1",
    )
    assert result.source == "ai_generated"
    assert result.grounding_status == "passed"
    assert result.citations == [EvidenceCitation(**citation)]
