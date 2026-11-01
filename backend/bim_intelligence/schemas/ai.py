"""Safe public contracts for AI explanations and application budget diagnostics."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from bim_intelligence.schemas.base import FrozenContractModel

ExplanationFallbackReason = Literal[
    "ai_disabled",
    "unsupported_evidence",
    "budget_limit",
    "ai_request_failed",
    "ai_output_invalid",
    "grounding_failed",
]


class EvidenceCitation(FrozenContractModel):
    """Exact deterministic provenance cited by one explanation."""

    finding_id: str = Field(min_length=1)
    global_id: str = Field(min_length=1)
    requirement_id: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    expected: str
    observed: str


class Explanation(FrozenContractModel):
    """Interpretation kept separate from immutable deterministic Finding records."""

    finding_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    probable_cause: str = Field(min_length=1)
    corrective_action: str = Field(min_length=1)
    citations: list[EvidenceCitation] = Field(default_factory=list)
    source: Literal["ai_generated", "deterministic_template"]
    grounding_status: Literal["passed", "fallback"]
    model: str | None = None
    fallback_reason: ExplanationFallbackReason | None = Field(
        default=None,
        description=(
            "Why a deterministic template was returned instead of an AI interpretation: "
            "``ai_disabled`` (no client configured), ``unsupported_evidence`` (evidence cannot "
            "be grounded safely), ``budget_limit`` (an application budget, call or token limit), "
            "``ai_request_failed``, ``ai_output_invalid`` (schema-invalid response) or "
            "``grounding_failed``. Always null for ``ai_generated``."
        ),
    )

    @model_validator(mode="after")
    def _label_matches_provenance(self) -> Explanation:
        if self.source == "ai_generated":
            if self.grounding_status != "passed" or self.fallback_reason is not None:
                raise ValueError("an ai_generated explanation must pass grounding without fallback")
            if not self.model:
                raise ValueError("an ai_generated explanation must name the model that produced it")
        elif (
            self.grounding_status != "fallback"
            or self.fallback_reason is None
            or self.model is not None
        ):
            raise ValueError(
                "a deterministic_template explanation must be a labelled fallback without a model"
            )
        return self


class BudgetStatus(FrozenContractModel):
    """Non-sensitive application-level accounting summary; never includes prompt content."""

    project_budget_usd: float = Field(ge=0)
    spent_usd: float = Field(ge=0)
    reserved_usd: float = Field(ge=0)
    remaining_usd: float = Field(ge=0)
    request_count: int = Field(ge=0)
