from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from bim_intelligence.bim import ModelIndex
from bim_intelligence.llm.client import FakeClient
from bim_intelligence.reporting.explanations import (
    ExplanationProvenanceError,
    explain_finding,
    verify_index_provenance,
)
from bim_intelligence.schemas import (
    CheckResult,
    CheckSpec,
    ElementRecord,
    ElementRef,
    EvidenceCitation,
    Explanation,
    Finding,
    InputManifest,
    ModelSummary,
    PlannedCheck,
    PropertyValue,
    Requirement,
    RequirementSource,
    ReviewPlan,
    ReviewRun,
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
    # Empty citations fail the response schema before the grounding check is reached.
    assert result.fallback_reason == "ai_output_invalid"
    assert result.model is None


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
    assert result.fallback_reason is None
    assert result.model == "fake-model"
    assert result.citations == [EvidenceCitation(**citation)]


def _citation(finding: Finding) -> dict[str, object]:
    return {
        "finding_id": finding.id,
        "global_id": finding.elements[0].global_id,
        "requirement_id": finding.requirement_id,
        "rule_id": finding.rule_id,
        "expected": finding.expected,
        "observed": finding.observed,
    }


def _draft(finding: Finding, **overrides: object) -> dict[str, object]:
    draft: dict[str, object] = {
        "finding_id": finding.id,
        "summary": "W-002 has FireRating 'TBC'; the requirement expects 'REI 60'.",
        "probable_cause": "The recorded value is TBC.",
        "corrective_action": "Replace TBC with REI 60.",
        "citations": [_citation(finding)],
    }
    draft.update(overrides)
    return draft


def test_without_a_client_the_template_is_labelled_ai_disabled() -> None:
    finding, requirement, index = _models()

    result = explain_finding(finding, requirement, index, None, run_id="run-1")

    assert result.source == "deterministic_template"
    assert result.fallback_reason == "ai_disabled"
    assert result.citations == [EvidenceCitation.model_validate(_citation(finding))]


def test_element_outside_the_index_is_unsupported_evidence_and_not_sent() -> None:
    finding, requirement, index = _models()
    empty = ModelIndex(summary=index.summary, elements=[])
    client = FakeClient([_draft(finding)])

    result = explain_finding(finding, requirement, empty, client, run_id="run-1")

    assert result.fallback_reason == "unsupported_evidence"
    assert client.calls == 0


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"corrective_action": "Replace TBC with REI 90."}, "grounding_failed"),
        ({"summary": "See REQ-999 for the rule."}, "grounding_failed"),
        ({"finding_id": "another-finding"}, "grounding_failed"),
        ({"citations": [{"global_id": "1" * 22}]}, "ai_output_invalid"),
        ({"unexpected": "field"}, "ai_output_invalid"),
    ],
)
def test_rejected_ai_output_is_labelled_with_the_rejection_reason(
    overrides: dict[str, object], reason: str
) -> None:
    finding, requirement, index = _models()

    result = explain_finding(
        finding, requirement, index, FakeClient([_draft(finding, **overrides)]), run_id="run-1"
    )

    assert result.source == "deterministic_template"
    assert result.fallback_reason == reason
    assert "90" not in result.corrective_action


def test_failed_request_is_labelled_ai_request_failed() -> None:
    finding, requirement, index = _models()

    result = explain_finding(finding, requirement, index, FakeClient([]), run_id="run-1")

    assert result.fallback_reason == "ai_request_failed"


def test_index_for_another_model_version_is_a_provenance_error() -> None:
    finding, _, index = _models()
    run = _run(finding, model_hash="1" * 64)

    with pytest.raises(ExplanationProvenanceError, match="model index"):
        verify_index_provenance(run, finding, index)


def test_indexed_element_that_differs_from_the_finding_is_a_provenance_error() -> None:
    finding, _, index = _models()
    record = index.elements[0]
    renamed = ModelIndex(
        summary=index.summary,
        elements=[record.model_copy(update={"ref": record.ref.model_copy(update={"name": "X"})})],
    )

    with pytest.raises(ExplanationProvenanceError, match="element"):
        verify_index_provenance(_run(finding), finding, renamed)


def test_element_absent_from_the_index_is_left_to_the_explainer() -> None:
    finding, _, index = _models()

    verify_index_provenance(_run(finding), finding, ModelIndex(summary=index.summary, elements=[]))


def _run(finding: Finding, *, model_hash: str = "0" * 64) -> ReviewRun:
    return ReviewRun(
        id="run-1",
        session_id="session-1",
        status="completed",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        finished_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        plan=ReviewPlan(checks=[PlannedCheck(check_id=finding.check_id, reason="Default.")]),
        plan_source="default",
        input_manifest=InputManifest(
            model_hash=model_hash,
            ids_hashes=["a" * 64],
            requirement_revisions={finding.requirement_id: 1},
            rule_versions={finding.rule_id: finding.rule_version},
        ),
        check_results=[
            CheckResult(
                check_id=finding.check_id,
                requirement_id=finding.requirement_id,
                status="failed",
                applicable_count=1,
                finding_ids=[finding.id],
            )
        ],
    )


_BASE = {
    "finding_id": "f",
    "summary": "s",
    "probable_cause": "c",
    "corrective_action": "a",
}


@pytest.mark.parametrize(
    "labels",
    [
        {"source": "ai_generated", "grounding_status": "fallback", "model": "m"},
        {"source": "ai_generated", "grounding_status": "passed", "model": None},
        {
            "source": "ai_generated",
            "grounding_status": "passed",
            "model": "m",
            "fallback_reason": "grounding_failed",
        },
        {"source": "deterministic_template", "grounding_status": "fallback"},
        {
            "source": "deterministic_template",
            "grounding_status": "passed",
            "fallback_reason": "ai_disabled",
        },
        {
            "source": "deterministic_template",
            "grounding_status": "fallback",
            "fallback_reason": "ai_disabled",
            "model": "m",
        },
    ],
)
def test_explanation_labels_must_match_their_provenance(labels: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Explanation.model_validate({**_BASE, **labels})


def test_consistent_explanation_labels_validate() -> None:
    ai = Explanation.model_validate(
        {**_BASE, "source": "ai_generated", "grounding_status": "passed", "model": "m"}
    )
    template = Explanation.model_validate(
        {
            **_BASE,
            "source": "deterministic_template",
            "grounding_status": "fallback",
            "fallback_reason": "budget_limit",
        }
    )
    token_limited = Explanation.model_validate(
        {
            **_BASE,
            "source": "deterministic_template",
            "grounding_status": "fallback",
            "fallback_reason": "token_limit",
        }
    )

    assert ai.fallback_reason is None
    assert template.model is None
    assert token_limited.fallback_reason == "token_limit"
