"""Requirement listing and explicit confirmation of the registered native check."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from bim_intelligence.api.deps import get_store
from bim_intelligence.api.errors import problem_responses
from bim_intelligence.requirements import confirm_classification_consistency
from bim_intelligence.schemas import Requirement
from bim_intelligence.store import SessionStore

router = APIRouter(tags=["requirements"])


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
