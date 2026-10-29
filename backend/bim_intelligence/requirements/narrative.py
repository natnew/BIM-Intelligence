"""Narrow narrative extraction: exact quotes and existing checks only (FR-REQ-01..04)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from bim_intelligence.config import Settings
from bim_intelligence.llm.client import ChatMessage, LLMClient
from bim_intelligence.llm.errors import LLMClientError, LLMOutputError
from bim_intelligence.schemas import (
    Requirement,
    RequirementCandidate,
    RequirementCandidateBatch,
    RequirementSource,
)
from bim_intelligence.store import SessionStore

_PROMPT = Path(__file__).parents[1] / "orchestration" / "prompts" / "requirements.v1.md"
_REQUIREMENT_ID_PREFIX = "REQ-"


class RequirementInterpretationError(ValueError):
    """A narrative requirement could not be safely extracted or confirmed."""


class _CandidateDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    location: str = Field(min_length=1)
    check_id: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class _CandidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[_CandidateDraft] = Field(default_factory=list)


@dataclass(frozen=True)
class _Segment:
    location: str
    text: str


def extract_candidates(
    client: LLMClient,
    *,
    document_id: str,
    document_kind: Literal["text", "markdown"],
    text: str,
    requirements: Sequence[Requirement],
    settings: Settings,
    run_id: str,
) -> RequirementCandidateBatch:
    if not text.strip():
        raise RequirementInterpretationError("The narrative document is empty.")
    segments = _segments(text)
    confirmed = [requirement for requirement in requirements if requirement.is_executable]
    by_check = {requirement.check.id: requirement for requirement in confirmed}
    payload = {
        "document_id": document_id,
        "paragraphs": [{"location": item.location, "text": item.text} for item in segments],
        "confirmed_checks": [
            {
                "check_id": check_id,
                "rule_id": requirement.check.rule_id,
                "kind": requirement.check.kind,
                "description": requirement.title,
                "statement": requirement.statement,
            }
            for check_id, requirement in sorted(by_check.items())
        ],
    }
    try:
        prompt = _PROMPT.read_text(encoding="utf-8")
    except OSError:
        raise RequirementInterpretationError(
            "The versioned requirement-extraction prompt is unavailable."
        ) from None
    try:
        completion = client.complete(
            [
                ChatMessage(role="system", content=prompt),
                ChatMessage(
                    role="user",
                    content=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                ),
            ],
            response_model=_CandidateResponse,
            max_output_tokens=settings.llm_max_output_tokens_per_call,
            purpose="requirement_extraction",
            run_id=run_id,
        )
    except LLMOutputError:
        raise RequirementInterpretationError(
            "Requirement output did not match the permitted schema."
        ) from None
    except LLMClientError:
        raise
    except ValidationError:
        raise RequirementInterpretationError("Requirement output is invalid.") from None

    candidates: list[RequirementCandidate] = []
    rejected = 0
    ids: set[str] = set()
    for draft in completion.value.candidates:
        segment = next((item for item in segments if item.location == draft.location), None)
        if (
            segment is None
            or not verify_candidate_quote(text, draft.quote)
            or not verify_candidate_quote(segment.text, draft.quote)
        ):
            rejected += 1
            continue
        if draft.check_id is not None and draft.check_id not in by_check:
            rejected += 1
            continue
        candidate_id = hashlib.sha256(
            f"{document_id}:{draft.location}:{draft.quote}".encode()
        ).hexdigest()[:16]
        if candidate_id in ids:
            rejected += 1
            continue
        ids.add(candidate_id)
        candidates.append(
            RequirementCandidate(
                id=candidate_id,
                title=draft.title,
                statement=draft.statement,
                source=RequirementSource(
                    document_id=document_id,
                    location=draft.location,
                    quote=draft.quote,
                ),
                document_kind=document_kind,
                check_id=draft.check_id,
                confidence=draft.confidence,
                status="proposed" if draft.check_id is not None else "informational",
            )
        )
    return RequirementCandidateBatch(
        document_id=document_id,
        document_kind=document_kind,
        candidates=candidates,
        rejected_count=rejected,
    )


def verify_candidate_quote(source_text: str, quote: str) -> bool:
    """A candidate quotation must be an exact, case-sensitive source substring."""
    return bool(quote) and quote in source_text


def confirm_candidate(
    store: SessionStore,
    session_id: str,
    candidate: RequirementCandidate,
    *,
    check_id: str,
    confirmed_by: str,
) -> Requirement:
    """Persist only a human-confirmed candidate bound to an existing confirmed CheckSpec."""
    if candidate.status != "proposed":
        raise RequirementInterpretationError(
            "Informational candidates cannot be compiled or executed."
        )
    if candidate.check_id != check_id:
        raise RequirementInterpretationError(
            "The confirmed CheckSpec must match the candidate's existing check."
        )
    expected_id = hashlib.sha256(
        f"{candidate.source.document_id}:{candidate.source.location}:"
        f"{candidate.source.quote}".encode()
    ).hexdigest()[:16]
    if candidate.id != expected_id:
        raise RequirementInterpretationError("Candidate identity does not match its source.")
    with store.lock_model(session_id) as lock:
        source = store.read_document(
            session_id,
            candidate.source.document_id,
            candidate.document_kind,
        )
        if hashlib.sha256(source).hexdigest() != candidate.source.document_id:
            raise RequirementInterpretationError("Stored source document failed integrity check.")
        try:
            original_text = source.decode("utf-8")
        except UnicodeDecodeError:
            raise RequirementInterpretationError(
                "The stored narrative document is unreadable."
            ) from None
        if not verify_candidate_quote(original_text, candidate.source.quote):
            raise RequirementInterpretationError(
                "Candidate quotation does not occur verbatim in the stored document."
            )
        if not any(
            segment.location == candidate.source.location
            and verify_candidate_quote(segment.text, candidate.source.quote)
            for segment in _segments(original_text)
        ):
            raise RequirementInterpretationError(
                "Candidate source identifier does not contain its quotation."
            )
        current = store.read_requirements(session_id)
        selected = next(
            (
                requirement
                for requirement in current
                if requirement.is_executable and requirement.check.id == check_id
            ),
            None,
        )
        if selected is None:
            raise RequirementInterpretationError(
                "The selected CheckSpec is not already confirmed for this session."
            )
        requirement = Requirement(
            id=f"{_REQUIREMENT_ID_PREFIX}{len(current) + 1:03d}",
            title=candidate.title,
            statement=candidate.statement,
            origin="document",
            source=candidate.source,
            check=selected.check,
            status="confirmed",
            revision=1,
            confirmed_revision=1,
            confirmed_by=confirmed_by,
            confirmed_at=store.now(),
        )
        store.write_requirements(lock, [*current, requirement])
        return requirement


def _segments(text: str) -> list[_Segment]:
    result: list[_Segment] = []
    chunks: list[str] = []
    paragraph = 0
    for line in text.splitlines(keepends=True):
        if line.strip():
            chunks.append(line)
        elif chunks:
            paragraph += 1
            result.append(_Segment(f"p-{paragraph:03d}", "".join(chunks)))
            chunks = []
    if chunks:
        paragraph += 1
        result.append(_Segment(f"p-{paragraph:03d}", "".join(chunks)))
    return result
