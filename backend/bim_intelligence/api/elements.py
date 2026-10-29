"""Element lookup by GlobalId (FR-ING-04)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from bim_intelligence.api.deps import get_store
from bim_intelligence.api.errors import problem_responses
from bim_intelligence.api.versioning import MODEL_CACHE_CONTROL, etag_for, resolve_model_version
from bim_intelligence.bim import load_index
from bim_intelligence.schemas import ElementRecord
from bim_intelligence.store import SessionStore

router = APIRouter(tags=["elements"])


@router.get(
    "/sessions/{session_id}/elements/{global_id}",
    response_model=ElementRecord,
    summary="Element record",
    description=(
        "The indexed record for one element: identity, type object, spatial container, "
        "property sets with instance/type provenance and classification references. "
        "The record comes from the index of the active model version; ``ETag`` is that "
        "version's quoted SHA-256 and ``If-Match`` with a different value returns 412, so a "
        "viewer that loaded one model can never be answered from another. "
        "A GlobalId carried by more than one element returns 409 and lists the express ids."
    ),
    responses=problem_responses(400, 404, 409, 412),
)
def get_element(
    session_id: str,
    global_id: str,
    request: Request,
    response: Response,
    store: SessionStore = Depends(get_store),
) -> ElementRecord:
    version = resolve_model_version(store, session_id, request)
    response.headers["ETag"] = etag_for(version)
    response.headers["Cache-Control"] = MODEL_CACHE_CONTROL
    return load_index(version).by_global_id(global_id)
