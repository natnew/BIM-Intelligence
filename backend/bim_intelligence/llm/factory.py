"""Create a request-scoped client without ever falling back to Live implicitly."""

from __future__ import annotations

from bim_intelligence.config import LLMMode, Settings
from bim_intelligence.llm.budget import BudgetLedger
from bim_intelligence.llm.client import LiveClient, LLMClient, RecordingClient, ReplayClient
from bim_intelligence.llm.errors import BudgetStateError


def create_budget_ledger(settings: Settings) -> BudgetLedger:
    input_price = settings.llm_price_input_per_m
    cached_input_price = settings.llm_price_cached_input_per_m
    output_price = settings.llm_price_output_per_m
    if input_price is None or cached_input_price is None or output_price is None:
        raise BudgetStateError("Muse Spark pricing is not configured; budget is unavailable.")
    return BudgetLedger(
        settings.data_dir / "llm" / "budget.json",
        project_budget_usd=settings.llm_project_budget_usd,
        run_budget_usd=settings.llm_max_run_budget_usd,
        call_budget_usd=settings.llm_max_call_budget_usd,
        input_price_per_m=input_price,
        cached_input_price_per_m=cached_input_price,
        output_price_per_m=output_price,
        max_calls_per_run=settings.llm_max_calls_per_run,
        max_input_tokens=settings.llm_max_input_tokens_per_call,
        max_output_tokens=max(
            settings.llm_max_output_tokens_per_call,
            settings.llm_max_planning_output_tokens,
            settings.llm_max_explanation_output_tokens,
        ),
    )


def create_client(settings: Settings) -> LLMClient | None:
    if settings.llm_mode is LLMMode.OFF:
        return None
    if settings.llm_mode is LLMMode.REPLAY:
        return ReplayClient(settings.llm_recordings_dir)
    live = LiveClient(settings, ledger=create_budget_ledger(settings))
    return RecordingClient(live, settings.llm_recordings_dir)
