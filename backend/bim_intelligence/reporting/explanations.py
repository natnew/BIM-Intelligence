"""Grounded, separately labelled explanations for deterministic findings (ADR-009)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from bim_intelligence.bim import UnknownElementError
from bim_intelligence.bim.model_index import ModelIndex
from bim_intelligence.llm.client import ChatMessage, LLMClient
from bim_intelligence.llm.errors import LLMClientError
from bim_intelligence.schemas import (
    ElementRecord,
    EvidenceCitation,
    Explanation,
    Finding,
    Requirement,
)

logger = logging.getLogger(__name__)
_PROMPT = Path(__file__).with_name("prompts") / "explanation.v1.md"
_GLOBAL_ID_RE = re.compile(r"\b[0-9A-Za-z_$]{22}\b")
_REQUIREMENT_ID_RE = re.compile(r"\bREQ-[A-Za-z0-9_-]+\b")
_NUMBER_RE = re.compile(r"(?<![\w.])[-+]?\d+(?:[.,]\d+)*(?!\w)")


class GroundingError(ValueError):
    """An explanation cites facts outside the deterministic evidence bundle."""


class _ExplanationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    probable_cause: str = Field(min_length=1)
    corrective_action: str = Field(min_length=1)
    citations: list[EvidenceCitation] = Field(min_length=1)


def explain_finding(
    finding: Finding,
    requirement: Requirement,
    index: ModelIndex,
    client: LLMClient | None,
    *,
    run_id: str,
    max_output_tokens: int = 500,
) -> Explanation:
    """Return a verified AI interpretation or a deterministic template, never a Finding."""
    records: list[ElementRecord] = []
    try:
        for element in finding.elements:
            records.append(index.by_express_id(element.express_id))
    except UnknownElementError:
        return deterministic_explanation(finding)
    if client is None or any(element.global_id is None for element in finding.elements):
        return deterministic_explanation(finding)
    if len(records) != 1:
        return deterministic_explanation(finding)
    try:
        prompt = _PROMPT.read_text(encoding="utf-8")
    except OSError:
        logger.warning("Versioned explanation prompt unavailable; deterministic fallback used.")
        return deterministic_explanation(finding)
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
    except (GroundingError, LLMClientError, OSError):
        logger.warning("AI explanation rejected; deterministic fallback used.")
        return deterministic_explanation(finding)
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


def deterministic_explanation(finding: Finding) -> Explanation:
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
    )


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
