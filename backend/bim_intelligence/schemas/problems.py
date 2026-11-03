"""RFC 9457 problem details: the single error shape for every endpoint (ARCHITECTURE §14)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from bim_intelligence.schemas.base import ContractModel

AIReviewFailureReason = Literal[
    "provider_unavailable",
    "provider_failure",
    "budget_limit",
    "budget_state",
    "token_limit",
    "invalid_output",
    "plan_rejected",
    "unsupported_scope",
    "replay_mismatch",
]


class AIReviewFailure(ContractModel):
    """Safe, typed provenance for a rejected AI-planning request."""

    mode: Literal["live", "replay", "off"]
    provider_request_attempted: bool
    model: str | None = Field(default=None, min_length=1)
    reason_code: AIReviewFailureReason


class ProblemDetail(ContractModel):
    """``application/problem+json`` body."""

    type: str = Field(default="about:blank", description="URI identifying the problem type.")
    title: str = Field(min_length=1, description="Short, stable summary of the problem type.")
    status: int = Field(ge=100, le=599)
    detail: str | None = Field(default=None, description="Occurrence-specific explanation.")
    instance: str | None = Field(default=None, description="URI of the specific occurrence.")
    correlation_id: str | None = Field(
        default=None, description="Request correlation id for matching against the run log."
    )
    ai_review_failure: AIReviewFailure | None = Field(
        default=None,
        description="Safe AI-planning failure provenance when an AI-required review is rejected.",
    )
