"""Session lifecycle (ARCHITECTURE §11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from bim_intelligence.api.deps import get_store
from bim_intelligence.api.errors import problem_responses
from bim_intelligence.schemas import Session
from bim_intelligence.store import SessionStore

router = APIRouter(tags=["sessions"])


@router.post(
    "/sessions",
    status_code=201,
    response_model=Session,
    summary="Create a review session",
    description=(
        "Creates an empty session and its storage directory. The response ``Location`` header "
        "points at the new session; upload a model with ``POST /sessions/{session_id}/model``."
    ),
)
def create_session(
    request: Request, response: Response, store: SessionStore = Depends(get_store)
) -> Session:
    session = store.create()
    response.headers["Location"] = request.url_for("get_session", session_id=session.id).path
    return session


@router.get(
    "/sessions/{session_id}",
    response_model=Session,
    summary="Session status",
    description="Session metadata: status and the hash of the stored model. Never exposes paths.",
    responses=problem_responses(400, 404),
)
def get_session(session_id: str, store: SessionStore = Depends(get_store)) -> Session:
    return store.get(session_id)
