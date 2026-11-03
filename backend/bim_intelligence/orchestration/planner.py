"""Bounded objective planning over confirmed immutable CheckSpecs (ADR-003, FR-REQ-06)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from bim_intelligence.config import Settings
from bim_intelligence.llm.client import ChatMessage, LLMClient
from bim_intelligence.llm.errors import LLMClientError, LLMOutputError
from bim_intelligence.schemas import (
    AIReviewFailureReason,
    ModelSummary,
    Requirement,
    ReviewPlan,
)


class PlanViolation(ValueError):  # noqa: N818
    """A model proposal references invalid, unconfirmed, duplicate or excessive checks."""

    def __init__(
        self,
        message: str,
        *,
        reason_code: AIReviewFailureReason = "plan_rejected",
        provider_request_attempted: bool = False,
        model: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.provider_request_attempted = provider_request_attempted
        self.model = model


class UnsupportedScopeViolation(PlanViolation):
    """No supplied confirmed check can represent the requested objective."""

    def __init__(
        self,
        *,
        provider_request_attempted: bool = False,
        model: str | None = None,
    ) -> None:
        super().__init__(
            "No supplied check applies to the requested objective.",
            reason_code="unsupported_scope",
            provider_request_attempted=provider_request_attempted,
            model=model,
        )


@dataclass(frozen=True)
class PlanProposal:
    """Accepted plan plus the model and network provenance returned by its client."""

    plan: ReviewPlan
    model: str
    provider_request_attempted: bool


_PROMPT = Path(__file__).with_name("prompts") / "planner.v2.md"


def propose_plan(
    client: LLMClient,
    *,
    objective: str,
    summary: ModelSummary,
    requirements: Sequence[Requirement],
    settings: Settings,
    run_id: str,
) -> PlanProposal:
    """Ask the model for JSON, then reject anything outside the confirmed check registry."""
    confirmed = [requirement for requirement in requirements if requirement.is_executable]
    by_check: dict[str, Requirement] = {}
    for requirement in confirmed:
        by_check.setdefault(requirement.check.id, requirement)
    if not by_check:
        raise UnsupportedScopeViolation()

    tools = [
        {
            "check_id": check_id,
            "rule_id": requirement.check.rule_id,
            "kind": requirement.check.kind,
            "description": requirement.title,
        }
        for check_id, requirement in sorted(by_check.items())
    ]
    user_payload = {
        "objective": objective,
        "model_summary": summary.model_dump(mode="json"),
        "confirmed_requirements": [
            {
                "requirement_id": requirement.id,
                "title": requirement.title,
                "statement": requirement.statement,
                "check_id": requirement.check.id,
            }
            for requirement in confirmed
        ],
        "available_checks": tools,
        "tool_description": (
            "Each check ID resolves server-side to one immutable IDS or registered native check. "
            "Execution is read-only and deterministic; the plan cannot pass parameters."
        ),
    }
    try:
        prompt = _PROMPT.read_text(encoding="utf-8")
    except OSError:
        raise PlanViolation("The versioned planner prompt is unavailable.") from None
    try:
        completion = client.complete(
            [
                ChatMessage(role="system", content=prompt),
                ChatMessage(role="user", content=_json_text(user_payload)),
            ],
            response_model=ReviewPlan,
            max_output_tokens=settings.llm_max_planning_output_tokens,
            purpose="plan",
            run_id=run_id,
        )
    except LLMOutputError as exc:
        raise PlanViolation(
            "Model plan did not match the permitted response schema.",
            reason_code="invalid_output",
            provider_request_attempted=exc.provider_request_attempted,
            model=exc.model,
        ) from None
    except LLMClientError:
        raise
    plan = completion.value
    try:
        _validate_plan(
            plan,
            by_check,
            max_checks=min(
                settings.max_plan_checks,
                settings.max_tool_calls_per_run,
            ),
        )
    except PlanViolation as exc:
        exc.provider_request_attempted = completion.provider_request_attempted
        exc.model = completion.model
        raise
    return PlanProposal(
        plan=plan,
        model=completion.model,
        provider_request_attempted=completion.provider_request_attempted,
    )


def validate_plan(
    plan: ReviewPlan,
    requirements: Sequence[Requirement],
    *,
    max_checks: int,
) -> dict[str, Requirement]:
    """Validate a plan independently, returning only server-resolved confirmed checks."""
    by_check: dict[str, Requirement] = {}
    for requirement in requirements:
        if requirement.is_executable:
            by_check.setdefault(requirement.check.id, requirement)
    _validate_plan(plan, by_check, max_checks=max_checks)
    return {item.check_id: by_check[item.check_id] for item in plan.checks}


def _validate_plan(
    plan: ReviewPlan,
    by_check: dict[str, Requirement],
    *,
    max_checks: int,
) -> None:
    ids = [item.check_id for item in plan.checks]
    if not ids:
        raise UnsupportedScopeViolation()
    if len(ids) != len(set(ids)):
        raise PlanViolation("A review plan contains duplicate check IDs.")
    unknown = sorted(set(ids) - by_check.keys())
    if unknown:
        raise PlanViolation("A review plan references an unknown or unconfirmed check.")
    if len(ids) > max_checks:
        raise PlanViolation(f"A review plan exceeds the {max_checks}-check execution cap.")


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
