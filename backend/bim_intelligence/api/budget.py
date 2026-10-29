"""Safe diagnostics for application-level model spending controls."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from bim_intelligence.api.errors import problem_responses
from bim_intelligence.config import Settings, get_settings
from bim_intelligence.orchestration import LLMClientError, create_budget_ledger
from bim_intelligence.schemas import BudgetStatus

router = APIRouter(tags=["AI diagnostics"])
logger = logging.getLogger(__name__)


@router.get(
    "/llm/budget",
    response_model=BudgetStatus,
    summary="Application-level LLM budget status",
    description=(
        "Returns non-sensitive application accounting from the persistent local ledger. These "
        "controls are safeguards in this application, not provider-enforced account spending "
        "caps. No prompts, API keys or private request contents are returned."
    ),
    responses=problem_responses(503),
)
def get_budget_status(settings: Settings = Depends(get_settings)) -> BudgetStatus:
    try:
        status = create_budget_ledger(settings).status()
    except LLMClientError as exc:
        logger.warning("Budget diagnostics unavailable (%s).", type(exc).__name__)
        raise HTTPException(
            status_code=503, detail="Budget diagnostics are temporarily unavailable."
        ) from None
    return BudgetStatus(
        project_budget_usd=float(status.project_budget_usd),
        spent_usd=float(status.spent_usd),
        reserved_usd=float(status.reserved_usd),
        remaining_usd=float(status.remaining_usd),
        request_count=status.request_count,
    )
