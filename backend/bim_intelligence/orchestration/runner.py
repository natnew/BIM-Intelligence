"""Execute a deterministic review run over one pinned model version (ADR-015 §4, ADR-018).

Lifecycle of :func:`run_review`:

1. Take the session's model lock. While it is held no upload can replace or prune the active
   version and no second run can start, so the version resolved in step 2 is the version every
   check sees (ADR-017 §4). Contention is reported, not queued: ``ModelLockedError`` → 409.
2. Resolve the active ``ModelVersion`` once; if the caller pinned a hash (``If-Match``) and it
   differs, refuse with ``ModelVersionMismatchError`` (412) rather than validating something
   else.
3. Build the default plan from the executable requirements and the ``InputManifest`` from the
   model hash, the IDS documents, the requirement revisions and the rule versions.
4. Open the IFC read-only from the version directory and run each planned check through
   ``validation``; a check that errors is recorded and the next one still runs.
5. Apply ``MAX_PLAN_CHECKS`` and ``MAX_TOOL_CALLS_PER_RUN`` in stable check order. Record
   unplanned or capped checks as ``skipped``; per-check errors do not stop later checks.
6. Publish ``run.json`` and ``findings.json`` together. The run is ``partial`` when coverage is
   incomplete because a check was skipped, errored or not applicable.

The run is synchronous: the caller receives the terminal ``ReviewRun``. An optional objective
uses the configured client to select confirmed checks before deterministic execution. Off mode
makes no model call; Live retains the existing approval and budget gates. No background task is
used (ADR-013 remains the design for longer runs).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from bim_intelligence.bim import load_index, load_summary
from bim_intelligence.config import LLMMode, Settings, get_settings
from bim_intelligence.llm.client import LLMClient
from bim_intelligence.llm.errors import (
    BudgetLimitError,
    BudgetStateError,
    LLMClientError,
    LLMOutputError,
    LLMUnavailableError,
    ReplayMismatchError,
    TokenLimitError,
)
from bim_intelligence.orchestration.default_plan import default_plan
from bim_intelligence.orchestration.planner import (
    PlanProposal,
    PlanViolation,
    UnsupportedScopeViolation,
    propose_plan,
    validate_plan,
)
from bim_intelligence.schemas import (
    AIReviewFailureReason,
    CheckResult,
    Finding,
    InputManifest,
    PlanSource,
    Requirement,
    ReviewMode,
    ReviewPlan,
    ReviewPlanOutcome,
    ReviewProvenance,
    ReviewRun,
    RunStatus,
    SelectedCheck,
    sort_findings,
)
from bim_intelligence.store import (
    MODEL_FILE,
    ModelVersion,
    ModelVersionMismatchError,
    SessionStore,
)
from bim_intelligence.validation import ValidationTarget

CheckObserver = Callable[[CheckResult], None]
logger = logging.getLogger(__name__)


class NoExecutableChecksError(Exception):
    """The session has no confirmed requirement to run (ARCHITECTURE §14: 409)."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"Session {session_id} has no confirmed requirements to review; upload an IDS "
            "document or explicitly confirm a registered native check first."
        )
        self.session_id = session_id


class ReviewScopeError(Exception):
    """A selected check is not current, confirmed and bound to the supplied revision."""

    def __init__(self) -> None:
        super().__init__("Selected review scope contains an unknown, stale, or unconfirmed check.")


class ReviewPlanningError(Exception):
    """A typed planning failure, safe to return without exposing prompts or provider details."""

    def __init__(
        self,
        *,
        mode: ReviewMode,
        reason_code: AIReviewFailureReason,
        provider_request_attempted: bool,
        model: str | None,
    ) -> None:
        super().__init__(_planning_failure_detail(reason_code))
        self.mode = mode
        self.reason_code = reason_code
        self.provider_request_attempted = provider_request_attempted
        self.model = model


class AIReviewRequiredError(ReviewPlanningError):
    """AI was required but no acceptable plan could be produced."""


class UnsupportedReviewScopeError(ReviewPlanningError):
    """The registered checks cannot represent the requested objective."""


@dataclass(frozen=True)
class ReviewOutcome:
    """A published run and the findings it verified, in canonical order."""

    run: ReviewRun
    findings: list[Finding]


def run_review(
    store: SessionStore,
    session_id: str,
    *,
    pinned_model_hash: str | None = None,
    observer: CheckObserver | None = None,
    settings: Settings | None = None,
    objective: str | None = None,
    client: LLMClient | None = None,
    ai_required: bool | None = None,
    continue_without_ai: bool = False,
    selected_checks: Sequence[SelectedCheck] | None = None,
) -> ReviewOutcome:
    """Run a bounded default or objective-selected plan against the active model and publish it.

    ``pinned_model_hash`` is the version the caller expects to be validated; a different active
    version is refused. ``observer`` is called with each ``CheckResult`` as it is produced (used
    for logging and, in tests, to exercise the lock while the run is in progress).
    """
    settings = settings or get_settings()
    effective_ai_required = objective is not None if ai_required is None else ai_required
    if effective_ai_required and objective is None:
        raise ValueError("An AI-required review needs a visible objective.")
    if continue_without_ai and not effective_ai_required:
        raise ValueError("Deterministic continuation requires an AI-required objective.")
    if objective is not None and not objective.strip():
        raise ValueError("A review objective must contain visible text.")

    with store.lock_model(session_id):
        version = store.active_model(session_id)
        if pinned_model_hash is not None and pinned_model_hash != version.sha256:
            raise ModelVersionMismatchError(session_id, pinned_model_hash, version.sha256)
        requirements = store.read_requirements(session_id)
        full_plan, all_by_check = default_plan(requirements)
        if not all_by_check:
            raise NoExecutableChecksError(session_id)
        requested_scope = _selected_scope(requirements, all_by_check, selected_checks)
        by_check = (
            all_by_check
            if selected_checks is None
            else {
                check_id: requested_scope[check_id]
                for check_id in all_by_check
                if check_id in requested_scope
            }
        )
        all_checks = list(by_check.items())
        run_id = store.new_id()
        scoped_plan = (
            full_plan
            if selected_checks is None
            else ReviewPlan(
                checks=[
                    full_plan_item
                    for full_plan_item in full_plan.checks
                    if full_plan_item.check_id in by_check
                ]
            )
        )
        plan = ReviewPlan(checks=scoped_plan.checks[: settings.max_plan_checks])
        plan_source: PlanSource = "default"
        ai_planning_requested = objective is not None
        execution_mode = (
            client.mode
            if objective is not None and not continue_without_ai and client is not None
            else settings.llm_mode
        )
        provider_request_attempted = False
        model: str | None = None
        planning_outcome: ReviewPlanOutcome = "not_requested"
        fallback_reason: str | None = None
        deterministic_fallback = False

        if continue_without_ai:
            planning_outcome = "continued_without_ai"
            fallback_reason = "user_selected_continue_without_ai"
            deterministic_fallback = True
        elif objective is not None:
            failure: LLMClientError | PlanViolation | None = None
            proposal: PlanProposal | None = None
            try:
                if client is None:
                    raise LLMUnavailableError("No AI planning client is configured.")
                proposal = propose_plan(
                    client,
                    objective=objective,
                    summary=load_summary(version),
                    requirements=list(by_check.values()),
                    settings=settings,
                    run_id=run_id,
                )
                selected = validate_plan(
                    proposal.plan,
                    list(by_check.values()),
                    max_checks=min(settings.max_plan_checks, settings.max_tool_calls_per_run),
                )
            except UnsupportedScopeViolation as exc:
                raise UnsupportedReviewScopeError(
                    mode=_review_mode(execution_mode),
                    reason_code="unsupported_scope",
                    provider_request_attempted=exc.provider_request_attempted,
                    model=exc.model,
                ) from None
            except (LLMClientError, PlanViolation) as exc:
                failure = exc

            if failure is not None:
                reason_code = _planning_failure_reason(failure)
                provider_request_attempted = failure.provider_request_attempted
                model = failure.model if isinstance(failure, PlanViolation) else None
                if reason_code == "unsupported_scope":
                    raise UnsupportedReviewScopeError(
                        mode=_review_mode(execution_mode),
                        reason_code=reason_code,
                        provider_request_attempted=provider_request_attempted,
                        model=model,
                    ) from None
                if effective_ai_required:
                    raise AIReviewRequiredError(
                        mode=_review_mode(execution_mode),
                        reason_code=reason_code,
                        provider_request_attempted=provider_request_attempted,
                        model=model,
                    ) from None
                logger.warning(
                    "AI plan rejected; deterministic default used (%s)",
                    type(failure).__name__,
                )
                planning_outcome = "rejected"
                fallback_reason = reason_code
                deterministic_fallback = True
            else:
                assert proposal is not None
                plan = proposal.plan
                provider_request_attempted = proposal.provider_request_attempted
                model = proposal.model
                plan_source = "llm"
                planning_outcome = "accepted"
                all_checks = list(selected.items()) + [
                    item for item in all_checks if item[0] not in selected
                ]
        planned_count = min(len(plan.checks), settings.max_plan_checks)
        attributed = list(by_check.values())
        manifest = _manifest(store, session_id, version, attributed)

        created_at = store.now()
        unplanned_reason = (
            "Not selected by the objective-specific review plan."
            if plan_source == "llm"
            else f"Skipped because MAX_PLAN_CHECKS={planned_count} was reached."
        )
        with ValidationTarget.open(version.path_for(MODEL_FILE), load_index(version)) as target:
            results, findings = _execute(
                target,
                all_checks,
                planned_count=planned_count,
                unplanned_reason=unplanned_reason,
                max_tool_calls=settings.max_tool_calls_per_run,
                observer=observer,
            )
        findings = sort_findings(findings)

        run = ReviewRun(
            id=run_id,
            session_id=session_id,
            status=_run_status(results),
            plan=plan,
            plan_source=plan_source,
            provenance=ReviewProvenance(
                ai_planning_requested=ai_planning_requested,
                provider_request_attempted=provider_request_attempted,
                mode=_review_mode(execution_mode),
                model=model,
                outcome=planning_outcome,
                fallback_reason=fallback_reason,
                deterministic_fallback=deterministic_fallback,
                selected_check_ids=(
                    [selection.check_id for selection in selected_checks]
                    if selected_checks is not None
                    else []
                ),
                executed_check_ids=[
                    result.check_id for result in results if result.status != "skipped"
                ],
            ),
            check_results=results,
            input_manifest=manifest,
            created_at=created_at,
            finished_at=store.now(),
        )
        store.publish_run(run, findings)
    return ReviewOutcome(run=run, findings=findings)


def _selected_scope(
    requirements: Sequence[Requirement],
    all_by_check: dict[str, Requirement],
    selected_checks: Sequence[SelectedCheck] | None,
) -> dict[str, Requirement]:
    if selected_checks is None:
        return all_by_check
    if not selected_checks:
        raise ReviewScopeError()
    by_requirement = {requirement.id: requirement for requirement in requirements}
    selected: dict[str, Requirement] = {}
    for selection in selected_checks:
        requirement = by_requirement.get(selection.requirement_id)
        if (
            requirement is None
            or not requirement.is_executable
            or requirement.revision != selection.requirement_revision
            or requirement.check.id != selection.check_id
            or selection.check_id in selected
        ):
            raise ReviewScopeError()
        selected[selection.check_id] = requirement
    return selected


def _planning_failure_reason(
    failure: LLMClientError | PlanViolation,
) -> AIReviewFailureReason:
    if isinstance(failure, PlanViolation):
        return failure.reason_code
    if isinstance(failure, LLMUnavailableError):
        return "provider_unavailable"
    if isinstance(failure, BudgetLimitError):
        return "budget_limit"
    if isinstance(failure, BudgetStateError):
        return "budget_state"
    if isinstance(failure, TokenLimitError):
        return "token_limit"
    if isinstance(failure, ReplayMismatchError):
        return "replay_mismatch"
    if isinstance(failure, LLMOutputError):
        return "invalid_output"
    return "provider_failure"


def _review_mode(mode: LLMMode) -> ReviewMode:
    modes: dict[LLMMode, ReviewMode] = {
        LLMMode.LIVE: "live",
        LLMMode.REPLAY: "replay",
        LLMMode.OFF: "off",
    }
    return modes[mode]


def _planning_failure_detail(reason: AIReviewFailureReason) -> str:
    details: dict[AIReviewFailureReason, str] = {
        "provider_unavailable": (
            "AI planning is unavailable in the configured mode. Continue without AI or ask the "
            "administrator to configure the approved provider."
        ),
        "provider_failure": "The configured provider could not complete the AI planning request.",
        "budget_limit": "The AI planning request was blocked by the configured spending limit.",
        "budget_state": (
            "AI planning was blocked because the spending ledger could not be verified."
        ),
        "token_limit": "The AI planning request exceeded a configured token limit.",
        "invalid_output": "The AI response did not match the permitted review-plan schema.",
        "plan_rejected": (
            "The proposed plan did not match the confirmed checks or configured execution caps."
        ),
        "unsupported_scope": (
            "No confirmed check in the selected scope can represent the requested objective."
        ),
        "replay_mismatch": "No matching offline Replay response is available.",
    }
    return details[reason]


def _execute(
    target: ValidationTarget,
    checks: Sequence[tuple[str, Requirement]],
    *,
    planned_count: int,
    unplanned_reason: str,
    max_tool_calls: int,
    observer: CheckObserver | None,
) -> tuple[list[CheckResult], list[Finding]]:
    results: list[CheckResult] = []
    findings: list[Finding] = []
    tool_calls = 0
    for position, (check_id, requirement) in enumerate(checks):
        if position >= planned_count:
            result = _skipped(check_id, requirement.id, unplanned_reason)
        elif tool_calls >= max_tool_calls:
            result = _skipped(
                check_id,
                requirement.id,
                f"Skipped because MAX_TOOL_CALLS_PER_RUN={max_tool_calls} was reached.",
            )
        else:
            tool_calls += 1
            try:
                outcome = target.run(requirement.check, requirement_id=requirement.id)
            except Exception as exc:
                logger.exception(
                    "check %s (%s) raised during deterministic execution",
                    check_id,
                    requirement.id,
                )
                result = CheckResult(
                    check_id=check_id,
                    requirement_id=requirement.id,
                    status="error",
                    applicable_count=0,
                    diagnostics=[f"{type(exc).__name__}: {exc}"],
                )
            else:
                result = outcome.result
                findings.extend(outcome.findings)
        results.append(result)
        if observer is not None:
            observer(result)
    return results, findings


def _skipped(check_id: str, requirement_id: str, diagnostic: str) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        requirement_id=requirement_id,
        status="skipped",
        applicable_count=0,
        diagnostics=[diagnostic],
    )


def _manifest(
    store: SessionStore,
    session_id: str,
    version: ModelVersion,
    requirements: Sequence[Requirement],
) -> InputManifest:
    ordered = sorted(requirements, key=lambda requirement: requirement.id)
    return InputManifest(
        model_hash=version.sha256,
        ids_hashes=sorted(store.get(session_id).document_hashes),
        requirement_revisions={r.id: r.revision for r in ordered},
        rule_versions={r.check.rule_id: r.check.rule_version for r in ordered},
    )


def _run_status(results: Sequence[CheckResult]) -> RunStatus:
    return (
        "partial"
        if any(result.status in {"error", "skipped", "not_applicable"} for result in results)
        else "completed"
    )
