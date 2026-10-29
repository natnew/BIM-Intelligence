"""Review orchestration (ADR-003): plan, execute deterministically, publish.

This slice contains the default plan and the synchronous deterministic runner. The LLM planner,
the tool registry and the bounded tool loop are later tasks and will sit beside them; every
plan they produce is filtered down to the same ``check_id``-only shape the runner executes.
"""

from bim_intelligence.orchestration.default_plan import DEFAULT_REASON, default_plan
from bim_intelligence.orchestration.runner import (
    CheckObserver,
    NoExecutableChecksError,
    ReviewOutcome,
    run_review,
)

__all__ = [
    "DEFAULT_REASON",
    "CheckObserver",
    "NoExecutableChecksError",
    "ReviewOutcome",
    "default_plan",
    "run_review",
]
