"""Element lookup by GlobalId (FR-ING-04)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from bim_intelligence.api.deps import get_store
from bim_intelligence.api.errors import problem_responses
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
        "A GlobalId carried by more than one element returns 409 and lists the express ids."
    ),
    responses=problem_responses(400, 404, 409),
)
def get_element(
    session_id: str, global_id: str, store: SessionStore = Depends(get_store)
) -> ElementRecord:
    return load_index(store, session_id).by_global_id(global_id)
