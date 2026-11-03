"""Review runs (FR-VAL-01, FR-REQ-07, ADR-015 §4, ADR-018, ADR-019).

In this slice a review is the bounded default plan of unique confirmed checks, executed
synchronously against the active model version; the response is the terminal ``ReviewRun``.
The handler is a synchronous ``def`` so IfcOpenShell and IfcTester work runs in FastAPI's
threadpool rather than on the event loop.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response

from bim_intelligence.api.deps import get_llm_client, get_store
from bim_intelligence.api.errors import problem_responses
from bim_intelligence.api.versioning import if_match_sha256
from bim_intelligence.config import Settings, get_settings
from bim_intelligence.orchestration import LLMClient, run_review
from bim_intelligence.schemas import CheckResult, ReviewRequest, ReviewRun
from bim_intelligence.store import SessionStore

router = APIRouter(tags=["reviews"])

logger = logging.getLogger(__name__)


@router.post(
    "/sessions/{session_id}/reviews",
    status_code=201,
    response_model=ReviewRun,
    summary="Run a bounded review",
    description=(
        "Executes a bounded plan against the active model version and returns the terminal "
        "``ReviewRun``. Without an objective, it uses the stable deterministic default plan. A "
        "supplied objective requires an accepted AI plan unless ``ai_required=false`` is explicit; "
        "strict failures return a typed problem rather than silently running the default. "
        "``continue_without_ai=true`` is the explicit deterministic alternative. The planner may "
        "select only checks in the current confirmed scope; rejected optional plans in a "
        "representable scope fall back to that scope's deterministic plan, while unsupported "
        "scope returns a typed 422. One ``CheckResult`` is recorded per unique check "
        "(``passed``, ``failed``, "
        "``error``, ``skipped`` or ``not_applicable``) and the ``InputManifest`` naming the "
        "model hash, IDS hashes, requirement revisions and rule versions it ran against. The "
        "session's lock is held for the duration, so an upload or a second review in the "
        "meantime is refused with 409 ``model-locked`` and the version can never change under "
        "the run. ``If-Match`` pins the run to a model version; a different active version is "
        "412 ``model-version-mismatch``. A session without a model is 404; one without "
        "confirmed requirements is 409 ``no-executable-checks``. The run ends ``partial`` when "
        "any check is skipped, not applicable or raises inside the engine; findings of the "
        "other checks are still recorded. ``MAX_PLAN_CHECKS`` limits the ordered plan and "
        "``MAX_TOOL_CALLS_PER_RUN`` limits executed checks; any cap hit is recorded as skipped. "
        "The model receives no tools and cannot alter validation criteria or create Findings. "
        "Live calls require explicit live-mode configuration and are bounded by the persistent "
        "application-level budget ledger."
    ),
    responses=problem_responses(400, 404, 409, 412, 422, 503),
)
def start_review(
    session_id: str,
    request: Request,
    response: Response,
    body: ReviewRequest | None = None,
    store: SessionStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
    client: LLMClient | None = Depends(get_llm_client),
) -> ReviewRun:
    outcome = run_review(
        store,
        session_id,
        pinned_model_hash=if_match_sha256(request),
        observer=_log_check,
        settings=settings,
        objective=body.objective if body else None,
        client=client,
        ai_required=body.effective_ai_required if body else False,
        continue_without_ai=body.continue_without_ai if body else False,
        selected_checks=body.selected_checks if body else None,
    )
    response.headers["Location"] = request.url_for(
        "get_review", session_id=session_id, run_id=outcome.run.id
    ).path
    return outcome.run


@router.get(
    "/sessions/{session_id}/reviews/{run_id}",
    response_model=ReviewRun,
    summary="Review run",
    description="A published run exactly as recorded; runs are immutable once published.",
    responses=problem_responses(400, 404),
)
def get_review(session_id: str, run_id: str, store: SessionStore = Depends(get_store)) -> ReviewRun:
    return store.read_run(session_id, run_id)


def _log_check(result: CheckResult) -> None:
    logger.info(
        "check %s (%s): %s, %d applicable, %d finding(s)",
        result.check_id,
        result.requirement_id,
        result.status,
        result.applicable_count,
        len(result.finding_ids),
    )
