"""Requirement listing and explicit confirmation of the registered native check."""

from __future__ import annotations

import hashlib
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from bim_intelligence.api.deps import get_llm_client, get_store
from bim_intelligence.api.errors import problem_responses
from bim_intelligence.config import Settings, get_settings
from bim_intelligence.orchestration import LLMClient, LLMClientError
from bim_intelligence.requirements import (
    confirm_candidate,
    confirm_classification_consistency,
    extract_candidates,
)
from bim_intelligence.schemas import (
    Requirement,
    RequirementCandidateBatch,
    RequirementCandidateConfirmation,
    RequirementExtractionRequest,
)
from bim_intelligence.store import SessionStore

router = APIRouter(tags=["requirements"])
logger = logging.getLogger(__name__)


@router.get(
    "/sessions/{session_id}/requirements",
    response_model=list[Requirement],
    summary="List requirements",
    description=(
        "Every requirement of the session in import order, each with its status, revision, "
        "source and the immutable ``CheckSpec`` it compiles to. Only requirements whose "
        "``confirmed_revision`` equals ``revision`` are executed by a review."
    ),
    responses=problem_responses(400, 404),
)
def list_requirements(
    session_id: str, store: SessionStore = Depends(get_store)
) -> list[Requirement]:
    return store.read_requirements(session_id)


@router.post(
    "/sessions/{session_id}/requirements/native/classification-consistency",
    status_code=201,
    response_model=Requirement,
    summary="Confirm the classification consistency check",
    description=(
        "Explicitly adds the registered P0 ``classification.consistent_by_type`` check as a "
        "confirmed built-in requirement. Its immutable CheckSpec is parameter-free and pinned "
        "to the registered rule version; it compares each classified type with its occurrences. "
        "The request is idempotent (200 when already present). An occurrence without a "
        "classified type is not applicable; classification presence remains an IDS check. "
        "The session lock prevents concurrent requirement writes or review execution."
    ),
    responses={
        200: {"model": Requirement, "description": "Check was already confirmed."},
        **problem_responses(400, 404, 409),
    },
)
def confirm_classification_check(
    session_id: str,
    request: Request,
    response: Response,
    store: SessionStore = Depends(get_store),
) -> Requirement:
    result = confirm_classification_consistency(store, session_id)
    response.status_code = 201 if result.created else 200
    response.headers["Location"] = request.url_for("list_requirements", session_id=session_id).path
    return result.requirement


@router.post(
    "/sessions/{session_id}/requirements/extract",
    response_model=RequirementCandidateBatch,
    summary="Extract unconfirmed narrative requirement candidates",
    description=(
        "Uses the configured offline or live client to identify candidates from a previously "
        "uploaded UTF-8 text or Markdown document. Exact quotes and paragraph identifiers are "
        "verified against the stored source. This endpoint creates no Requirement; only a "
        "candidate mapped to an existing confirmed CheckSpec can be confirmed separately."
    ),
    responses=problem_responses(400, 404, 409, 422, 503),
)
def extract_requirement_candidates(
    session_id: str,
    body: RequirementExtractionRequest,
    store: SessionStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
    client: LLMClient | None = Depends(get_llm_client),
) -> RequirementCandidateBatch:
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Requirement interpretation is disabled because LLM_MODE is off.",
        )
    source = store.read_document(session_id, body.document_id, body.document_kind)
    if hashlib.sha256(source).hexdigest() != body.document_id:
        raise HTTPException(
            status_code=422, detail="Stored source document failed integrity check."
        )
    try:
        text = source.decode("utf-8-sig")
        return extract_candidates(
            client,
            document_id=body.document_id,
            document_kind=body.document_kind,
            text=text,
            requirements=store.read_requirements(session_id),
            settings=settings,
            run_id=str(uuid.uuid4()),
        )
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422,
            detail="Narrative requirements document is not valid UTF-8 text.",
        ) from None
    except LLMClientError as exc:
        logger.warning("Requirement interpretation failed (%s).", type(exc).__name__)
        raise HTTPException(
            status_code=503, detail="Requirement interpretation is temporarily unavailable."
        ) from None


@router.post(
    "/sessions/{session_id}/requirements/confirm-candidate",
    response_model=Requirement,
    status_code=201,
    summary="Confirm a narrative requirement candidate",
    description=(
        "Explicitly confirms one proposed candidate against an already confirmed immutable "
        "CheckSpec. The quote, source paragraph, document hash and candidate identity are "
        "revalidated against the stored source. Informational or unmapped candidates cannot be "
        "compiled or executed."
    ),
    responses=problem_responses(400, 404, 409, 422),
)
def confirm_requirement_candidate(
    session_id: str,
    body: RequirementCandidateConfirmation,
    request: Request,
    response: Response,
    store: SessionStore = Depends(get_store),
) -> Requirement:
    requirement = confirm_candidate(
        store,
        session_id,
        body.candidate,
        check_id=body.check_id,
        confirmed_by=body.confirmed_by,
    )
    response.headers["Location"] = request.url_for("list_requirements", session_id=session_id).path
    return requirement
