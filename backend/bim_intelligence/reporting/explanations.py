"""Grounded, separately labelled explanations for deterministic findings (ADR-009).

An explanation is an interpretation of one immutable ``Finding``; it never creates, edits or
persists a Finding. Before any evidence is assembled, :func:`resolve_finding_provenance` and
:func:`verify_index_provenance` confirm that the finding, its check, its confirmed requirement
revision, its source document and its model elements are exactly those the run recorded.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from bim_intelligence.bim import UnknownElementError
from bim_intelligence.bim.model_index import ModelIndex
from bim_intelligence.llm.client import ChatMessage, LLMClient
from bim_intelligence.llm.errors import (
    BudgetLimitError,
    LLMClientError,
    LLMOutputError,
    TokenLimitError,
)
from bim_intelligence.schemas import (
    ElementRecord,
    EvidenceCitation,
    Explanation,
    ExplanationFallbackReason,
    Finding,
    Requirement,
    ReviewRun,
)

logger = logging.getLogger(__name__)
_PROMPT = Path(__file__).with_name("prompts") / "explanation.v1.md"
_GLOBAL_ID_RE = re.compile(r"\b[0-9A-Za-z_$]{22}\b")
_REQUIREMENT_ID_RE = re.compile(r"\bREQ-[A-Za-z0-9_-]+\b")
_NUMBER_RE = re.compile(r"(?<![\w.])[-+]?\d+(?:[.,]\d+)*(?!\w)")


class GroundingError(ValueError):
    """An explanation cites facts outside the deterministic evidence bundle."""


class FindingNotInRunError(LookupError):
    """The requested finding is not one the run recorded."""

    def __init__(self, session_id: str, run_id: str, finding_id: str) -> None:
        super().__init__(
            f"Session {session_id}: run {run_id} did not record finding {finding_id[:16]}."
        )
        self.session_id = session_id
        self.run_id = run_id
        self.finding_id = finding_id


class ExplanationProvenanceError(ValueError):
    """The stored evidence no longer matches what the run verified; nothing is explained."""

    def __init__(self, run_id: str, reason: str) -> None:
        super().__init__(f"Run {run_id}: {reason} No explanation was produced.")
        self.run_id = run_id
        self.reason = reason


class RunModelMismatchError(ValueError):
    """The client asserted a model version other than the one the run validated."""

    def __init__(self, run_id: str, expected: str, run_model_hash: str) -> None:
        super().__init__(
            f"Run {run_id} validated model version {run_model_hash} but the request names "
            f"{expected}. Reload the run's model before requesting an explanation."
        )
        self.run_id = run_id
        self.expected = expected
        self.run_model_hash = run_model_hash


class _ExplanationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    probable_cause: str = Field(min_length=1)
    corrective_action: str = Field(min_length=1)
    citations: list[EvidenceCitation] = Field(min_length=1)


def resolve_finding_provenance(
    session_id: str,
    run: ReviewRun,
    findings: list[Finding],
    requirements: list[Requirement],
    finding_id: str,
) -> tuple[Finding, Requirement]:
    """The recorded finding and the exact confirmed requirement revision that produced it.

    Raises :class:`FindingNotInRunError` when the run did not record the finding and
    :class:`ExplanationProvenanceError` when any link between run, check result, finding,
    requirement, check and source document no longer agrees with the run's input manifest.
    """
    if run.session_id != session_id:
        raise ExplanationProvenanceError(run.id, "The run belongs to a different session.")
    owning = [result for result in run.check_results if finding_id in result.finding_ids]
    finding = next((item for item in findings if item.id == finding_id), None)
    if not owning or finding is None:
        raise FindingNotInRunError(session_id, run.id, finding_id)
    if len(owning) != 1:
        raise ExplanationProvenanceError(run.id, "The finding is attributed to several checks.")
    result = owning[0]
    if result.check_id != finding.check_id or result.requirement_id != finding.requirement_id:
        raise ExplanationProvenanceError(
            run.id, "The finding does not match the check result that recorded it."
        )
    manifest = run.input_manifest
    revision = manifest.requirement_revisions.get(finding.requirement_id)
    if revision is None:
        raise ExplanationProvenanceError(
            run.id, "The finding's requirement is not in the run's input manifest."
        )
    requirement = next(
        (
            item
            for item in requirements
            if item.id == finding.requirement_id and item.revision == revision
        ),
        None,
    )
    if requirement is None:
        raise ExplanationProvenanceError(
            run.id, "The requirement revision used by this run is no longer available."
        )
    if not requirement.is_executable:
        raise ExplanationProvenanceError(
            run.id, "The requirement revision used by this run is no longer confirmed."
        )
    check = requirement.check
    if (
        check.id != finding.check_id
        or check.rule_id != finding.rule_id
        or check.rule_version != finding.rule_version
        or manifest.rule_versions.get(finding.rule_id) != finding.rule_version
    ):
        raise ExplanationProvenanceError(
            run.id, "The confirmed check no longer matches the check that produced the finding."
        )
    if requirement.origin != "builtin" and requirement.source is None:
        raise ExplanationProvenanceError(
            run.id, "The requirement's source document reference is missing."
        )
    if requirement.source is not None and requirement.source.document_id not in set(
        manifest.ids_hashes
    ):
        raise ExplanationProvenanceError(
            run.id, "The requirement's source document is not in the run's input manifest."
        )
    return finding, requirement


def verify_index_provenance(run: ReviewRun, finding: Finding, index: ModelIndex) -> None:
    """Confirm the index is the run's pinned model version and agrees with the finding.

    An element the index does not hold is not a mismatch: findings may cite entities outside
    the index, and :func:`explain_finding` labels those as ``unsupported_evidence``. An indexed
    element whose reference differs from the finding's is a mismatch.
    """
    if index.summary.model_hash != run.input_manifest.model_hash:
        raise ExplanationProvenanceError(
            run.id, "The model index does not match the run's model version."
        )
    for element in finding.elements:
        try:
            record = index.by_express_id(element.express_id)
        except UnknownElementError:
            continue
        if record.ref != element:
            raise ExplanationProvenanceError(
                run.id, "A finding element differs from the run's model version."
            )


def explain_finding(
    finding: Finding,
    requirement: Requirement,
    index: ModelIndex,
    client: LLMClient | None,
    *,
    run_id: str,
    max_output_tokens: int = 500,
) -> Explanation:
    """Return a verified AI interpretation or a labelled deterministic template, never a Finding."""
    records: list[ElementRecord] = []
    try:
        for element in finding.elements:
            records.append(index.by_express_id(element.express_id))
    except UnknownElementError:
        return deterministic_explanation(finding, reason="unsupported_evidence")
    if client is None:
        return deterministic_explanation(finding, reason="ai_disabled")
    if any(element.global_id is None for element in finding.elements) or len(records) != 1:
        return deterministic_explanation(finding, reason="unsupported_evidence")
    try:
        prompt = _PROMPT.read_text(encoding="utf-8")
    except OSError:
        logger.warning("Versioned explanation prompt unavailable; deterministic fallback used.")
        return deterministic_explanation(finding, reason="ai_request_failed")
    evidence = {
        "finding": finding.model_dump(mode="json"),
        "confirmed_requirement": requirement.model_dump(mode="json"),
        "model_index_elements": [record.model_dump(mode="json") for record in records],
    }
    try:
        completion = client.complete(
            [
                ChatMessage(role="system", content=prompt),
                ChatMessage(
                    role="user",
                    content=json.dumps(evidence, ensure_ascii=False, sort_keys=True),
                ),
            ],
            response_model=_ExplanationDraft,
            max_output_tokens=max_output_tokens,
            purpose="explanation",
            run_id=run_id,
        )
        _verify_grounding(completion.value, finding, requirement, records)
    except (GroundingError, LLMClientError, OSError) as exc:
        reason = _fallback_reason(exc)
        logger.warning("AI explanation rejected (%s); deterministic fallback used.", reason)
        return deterministic_explanation(finding, reason=reason)
    return Explanation(
        finding_id=finding.id,
        summary=completion.value.summary,
        probable_cause=completion.value.probable_cause,
        corrective_action=completion.value.corrective_action,
        citations=completion.value.citations,
        source="ai_generated",
        grounding_status="passed",
        model=completion.model,
    )


def deterministic_explanation(
    finding: Finding, *, reason: ExplanationFallbackReason
) -> Explanation:
    """A template restating the verified finding, labelled with why AI was not used."""
    citations = [
        EvidenceCitation(
            finding_id=finding.id,
            global_id=element.global_id,
            requirement_id=finding.requirement_id,
            rule_id=finding.rule_id,
            expected=finding.expected,
            observed=finding.observed,
        )
        for element in finding.elements
        if element.global_id is not None
    ]
    return Explanation(
        finding_id=finding.id,
        summary=f"{finding.observed} The verified check expected {finding.expected}",
        probable_cause="The deterministic check found that the recorded value did not match.",
        corrective_action=(
            "Review the cited requirement and correct the recorded model value before "
            "re-running the deterministic check."
        ),
        citations=citations,
        source="deterministic_template",
        grounding_status="fallback",
        fallback_reason=reason,
    )


def _fallback_reason(exc: Exception) -> ExplanationFallbackReason:
    if isinstance(exc, GroundingError):
        return "grounding_failed"
    if isinstance(exc, LLMOutputError):
        return "ai_output_invalid"
    if isinstance(exc, (BudgetLimitError, TokenLimitError)):
        return "budget_limit"
    return "ai_request_failed"


def _verify_grounding(
    draft: _ExplanationDraft,
    finding: Finding,
    requirement: Requirement,
    records: list[ElementRecord],
) -> None:
    if draft.finding_id != finding.id:
        raise GroundingError("Explanation references another finding.")
    if len(draft.citations) != len(finding.elements) or len(records) != len(finding.elements):
        raise GroundingError("Explanation citation count does not match the finding elements.")
    expected_by_global_id = {
        element.global_id: element for element in finding.elements if element.global_id is not None
    }
    citations_by_global_id = {citation.global_id: citation for citation in draft.citations}
    if (
        len(citations_by_global_id) != len(draft.citations)
        or citations_by_global_id.keys() != expected_by_global_id.keys()
    ):
        raise GroundingError("Explanation mixes or omits element evidence.")
    for global_id, citation in citations_by_global_id.items():
        matching_record = next(
            (record for record in records if record.ref.global_id == global_id), None
        )
        if (
            citation.finding_id != finding.id
            or citation.requirement_id != requirement.id
            or citation.rule_id != finding.rule_id
            or citation.expected != finding.expected
            or citation.observed != finding.observed
            or expected_by_global_id[global_id].global_id != global_id
            or matching_record is None
        ):
            raise GroundingError("Explanation citation differs from the verified finding.")
    evidence_text = " ".join(
        [
            finding.expected,
            finding.observed,
            requirement.title,
            requirement.statement,
            requirement.source.quote if requirement.source else "",
            *[
                json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
                for record in records
            ],
            finding.id,
            finding.requirement_id,
            finding.rule_id,
        ]
    )
    narrative = " ".join((draft.summary, draft.probable_cause, draft.corrective_action))
    allowed_global_ids = set(expected_by_global_id)
    if any(global_id not in allowed_global_ids for global_id in _GLOBAL_ID_RE.findall(narrative)):
        raise GroundingError("Explanation mentions an element outside this finding.")
    allowed_requirement_ids = set(_REQUIREMENT_ID_RE.findall(evidence_text))
    if any(
        requirement_id not in allowed_requirement_ids
        for requirement_id in _REQUIREMENT_ID_RE.findall(narrative)
    ):
        raise GroundingError("Explanation mentions an unknown requirement.")
    narrative_without_ids = _GLOBAL_ID_RE.sub("", narrative)
    allowed_numbers = set(_NUMBER_RE.findall(evidence_text))
    if any(number not in allowed_numbers for number in _NUMBER_RE.findall(narrative_without_ids)):
        raise GroundingError("Explanation contains an unsupported numeric value.")
