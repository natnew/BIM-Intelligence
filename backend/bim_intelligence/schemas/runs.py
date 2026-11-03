"""Review runs, plans and per-check execution status (C-01, C-05).

A ``CheckResult`` records how a check *executed*; a ``Finding`` records a verified defect.
Keeping them apart means an error, a cap hit or zero applicability can never read as
compliance or enter the precision denominator.
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from bim_intelligence.schemas.base import ContractModel, FrozenContractModel
from bim_intelligence.schemas.elements import Sha256Hex

CheckStatus = Literal["passed", "failed", "error", "skipped", "not_applicable"]
RunStatus = Literal["queued", "running", "completed", "partial", "failed", "interrupted"]
PlanSource = Literal["llm", "default"]
ReviewMode = Literal["live", "replay", "off"]
ReviewPlanOutcome = Literal["not_requested", "accepted", "rejected", "continued_without_ai"]

TERMINAL_RUN_STATUSES: frozenset[str] = frozenset({"completed", "partial", "failed", "interrupted"})


class PlannedCheck(FrozenContractModel):
    """A plan item: which confirmed check to run and why. Never carries parameters."""

    check_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ReviewPlan(FrozenContractModel):
    """The ordered set of checks a run intends to execute (plan-then-execute, C-01)."""

    checks: list[PlannedCheck] = Field(default_factory=list)


class SelectedCheck(FrozenContractModel):
    """A user-selected check pinned to the confirmed requirement revision it came from."""

    check_id: str = Field(min_length=1)
    requirement_id: str = Field(min_length=1)
    requirement_revision: int = Field(ge=1)


class ReviewRequest(FrozenContractModel):
    """Bounded review intent; an objective requires AI unless explicitly made optional."""

    objective: str | None = Field(
        default=None,
        min_length=1,
        max_length=4_000,
        pattern=r"\S",
        description=(
            "Plain-language review objective. It must contain visible text; whitespace-only "
            "objectives are rejected rather than sent to the planner."
        ),
    )
    ai_required: bool | None = Field(
        default=None,
        description=(
            "Whether an objective requires an accepted AI plan. When omitted, a supplied "
            "objective requires AI; a request without an objective uses the deterministic plan."
        ),
    )
    continue_without_ai: bool = Field(
        default=False,
        description="Explicitly choose the deterministic alternative after an AI-required request.",
    )
    selected_checks: list[SelectedCheck] | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description=(
            "Optional confirmed-check scope, each pinned to its requirement revision. The model "
            "may select only within this scope."
        ),
    )

    @model_validator(mode="after")
    def _review_policy_is_consistent(self) -> ReviewRequest:
        effective_ai_required = (
            self.ai_required if self.ai_required is not None else self.objective is not None
        )
        if self.ai_required is True and self.objective is None:
            raise ValueError("ai_required requires a visible review objective")
        if self.continue_without_ai and not effective_ai_required:
            raise ValueError("continue_without_ai requires an AI-required objective")
        if self.selected_checks is not None:
            ids = [selected.check_id for selected in self.selected_checks]
            if len(ids) != len(set(ids)):
                raise ValueError("selected_checks must not contain duplicate check_id values")
        return self

    @property
    def effective_ai_required(self) -> bool:
        """Resolve the backwards-compatible policy for callers that send an objective."""
        return self.ai_required if self.ai_required is not None else self.objective is not None


class ReviewProvenance(FrozenContractModel):
    """Persisted AI planning and execution provenance; absent on historical runs."""

    ai_planning_requested: bool
    provider_request_attempted: bool
    mode: ReviewMode
    model: str | None = Field(default=None, min_length=1)
    outcome: ReviewPlanOutcome
    fallback_reason: str | None = None
    deterministic_fallback: bool = False
    selected_check_ids: list[str] = Field(default_factory=list)
    executed_check_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _provenance_is_consistent(self) -> ReviewProvenance:
        if self.provider_request_attempted and self.mode != "live":
            raise ValueError("provider_request_attempted requires live mode")
        if self.outcome == "not_requested" and self.ai_planning_requested:
            raise ValueError("outcome 'not_requested' cannot have an AI planning request")
        if self.outcome != "not_requested" and not self.ai_planning_requested:
            raise ValueError("this planning outcome requires an AI planning request")
        if self.outcome == "accepted" and self.deterministic_fallback:
            raise ValueError("an accepted AI plan cannot be a deterministic fallback")
        if self.outcome in {"rejected", "continued_without_ai"} and (
            not self.deterministic_fallback or self.fallback_reason is None
        ):
            raise ValueError("a deterministic fallback requires a reason")
        if self.outcome in {"not_requested", "accepted"} and self.fallback_reason is not None:
            raise ValueError("this planning outcome must not have a fallback reason")
        for field_name, values in (
            ("selected_check_ids", self.selected_check_ids),
            ("executed_check_ids", self.executed_check_ids),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self


class CheckResult(ContractModel):
    """Execution outcome of one planned check."""

    check_id: str = Field(min_length=1)
    requirement_id: str = Field(min_length=1)
    status: CheckStatus
    applicable_count: int = Field(ge=0, description="Elements the check applied to.")
    finding_ids: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(
        default_factory=list, description="Engine messages; required for status 'error'."
    )

    @model_validator(mode="after")
    def _status_and_findings_agree(self) -> CheckResult:
        if self.status == "failed" and not self.finding_ids:
            raise ValueError("status 'failed' requires at least one entry in finding_ids")
        if self.status != "failed" and self.finding_ids:
            raise ValueError(f"status {self.status!r} must not carry finding_ids")
        if self.status == "not_applicable" and self.applicable_count != 0:
            raise ValueError("status 'not_applicable' requires applicable_count == 0")
        if self.status == "error" and not self.diagnostics:
            raise ValueError("status 'error' requires at least one diagnostics message")
        return self


class InputManifest(FrozenContractModel):
    """Everything that determines a run's findings; two runs with equal manifests must agree."""

    model_hash: Sha256Hex
    ids_hashes: list[Sha256Hex] = Field(default_factory=list)
    requirement_revisions: dict[str, int] = Field(default_factory=dict)
    rule_versions: dict[str, str] = Field(default_factory=dict)


class ReviewRun(ContractModel):
    """One review run over a session; the only record that carries timestamps."""

    id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    status: RunStatus
    plan: ReviewPlan
    plan_source: PlanSource
    provenance: ReviewProvenance | None = None
    check_results: list[CheckResult] = Field(default_factory=list)
    input_manifest: InputManifest
    created_at: AwareDatetime
    finished_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def _terminal_status_has_finished_at(self) -> ReviewRun:
        terminal = self.status in TERMINAL_RUN_STATUSES
        if terminal and self.finished_at is None:
            raise ValueError(f"status {self.status!r} requires finished_at")
        if not terminal and self.finished_at is not None:
            raise ValueError(f"status {self.status!r} must not carry finished_at")
        if self.finished_at is not None and self.finished_at < self.created_at:
            raise ValueError("finished_at must not be earlier than created_at")
        return self

    @model_validator(mode="after")
    def _one_result_per_check(self) -> ReviewRun:
        check_ids = [result.check_id for result in self.check_results]
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("check_results must contain at most one entry per check_id")
        return self

    @property
    def finding_ids(self) -> list[str]:
        return [finding_id for result in self.check_results for finding_id in result.finding_ids]
