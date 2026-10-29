"""Safe public contracts for AI explanations and application budget diagnostics."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from bim_intelligence.schemas.base import FrozenContractModel


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


class BudgetStatus(FrozenContractModel):
    """Non-sensitive application-level accounting summary; never includes prompt content."""

    project_budget_usd: float = Field(ge=0)
    spent_usd: float = Field(ge=0)
    reserved_usd: float = Field(ge=0)
    remaining_usd: float = Field(ge=0)
    request_count: int = Field(ge=0)
