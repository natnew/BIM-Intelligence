"""Requirement listing (ARCHITECTURE §11). Confirmation and editing arrive with BEP extraction."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from bim_intelligence.api.deps import get_store
from bim_intelligence.api.errors import problem_responses
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
