"""The default review plan: every executable requirement, once per check (FR-REQ-07, ADR-003).

This is the plan a run uses when no planner is involved (``plan_source="default"``) and the
plan every LLM-proposed plan is filtered against later. It carries only check ids and reasons;
no parameters can enter a plan (ADR-015 §1).
"""

from __future__ import annotations

from collections.abc import Sequence

from bim_intelligence.requirements import executable_requirements
from bim_intelligence.schemas import PlannedCheck, Requirement, ReviewPlan

DEFAULT_REASON = "Confirmed requirement; included by the default pre-issue review plan."


def default_plan(
    requirements: Sequence[Requirement],
) -> tuple[ReviewPlan, dict[str, Requirement]]:
    """The plan and, for each planned check id, the requirement it is attributed to.

    Requirements are visited in id order so that attribution is stable across runs. Two
    requirements compiled to the same ``CheckSpec`` (identical criteria) run once, attributed to
    the first; the run records one ``CheckResult`` per check id by contract.
    """
    by_check: dict[str, Requirement] = {}
    for requirement in sorted(executable_requirements(requirements), key=lambda r: r.id):
        by_check.setdefault(requirement.check.id, requirement)
    plan = ReviewPlan(
        checks=[PlannedCheck(check_id=check_id, reason=DEFAULT_REASON) for check_id in by_check]
    )
    return plan, by_check
