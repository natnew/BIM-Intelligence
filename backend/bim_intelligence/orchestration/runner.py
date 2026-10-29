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

The run is synchronous: the caller receives the terminal ``ReviewRun``. No network access, no
language model, no background task (ADR-013 remains the design for longer runs).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from bim_intelligence.bim import load_index, load_summary
from bim_intelligence.config import Settings, get_settings
from bim_intelligence.llm.client import LLMClient
from bim_intelligence.llm.errors import LLMClientError
from bim_intelligence.orchestration.default_plan import default_plan
from bim_intelligence.orchestration.planner import PlanViolation, propose_plan, validate_plan
from bim_intelligence.schemas import (
    CheckResult,
    Finding,
    InputManifest,
    PlanSource,
    Requirement,
    ReviewPlan,
    ReviewRun,
    RunStatus,
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
) -> ReviewOutcome:
    """Run the default plan against the session's active model and publish the result.

    ``pinned_model_hash`` is the version the caller expects to be validated; a different active
    version is refused. ``observer`` is called with each ``CheckResult`` as it is produced (used
    for logging and, in tests, to exercise the lock while the run is in progress).
    """
    settings = settings or get_settings()
    with store.lock_model(session_id):
        version = store.active_model(session_id)
        if pinned_model_hash is not None and pinned_model_hash != version.sha256:
            raise ModelVersionMismatchError(session_id, pinned_model_hash, version.sha256)
        full_plan, by_check = default_plan(store.read_requirements(session_id))
        all_checks = list(by_check.items())
        if not all_checks:
            raise NoExecutableChecksError(session_id)
        run_id = store.new_id()
        plan = ReviewPlan(checks=full_plan.checks[: settings.max_plan_checks])
        plan_source: PlanSource = "default"
        if objective is not None and client is not None:
            try:
                proposed = propose_plan(
                    client,
                    objective=objective,
                    summary=load_summary(version),
                    requirements=list(by_check.values()),
                    settings=settings,
                    run_id=run_id,
                )
                selected = validate_plan(
                    proposed,
                    list(by_check.values()),
                    max_checks=min(settings.max_plan_checks, settings.max_tool_calls_per_run),
                )
            except (LLMClientError, PlanViolation) as exc:
                logger.warning(
                    "AI plan rejected; deterministic default used (%s)", type(exc).__name__
                )
            else:
                plan = proposed
                plan_source = "llm"
                all_checks = list(selected.items()) + [
                    item for item in all_checks if item[0] not in selected
                ]
        planned_count = min(len(plan.checks), settings.max_plan_checks)
        attributed = [requirement for _, requirement in by_check.items()]
        manifest = _manifest(store, session_id, version, attributed)

        created_at = store.now()
        with ValidationTarget.open(version.path_for(MODEL_FILE), load_index(version)) as target:
            results, findings = _execute(
                target,
                all_checks,
                planned_count=planned_count,
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
            check_results=results,
            input_manifest=manifest,
            created_at=created_at,
            finished_at=store.now(),
        )
        store.publish_run(run, findings)
    return ReviewOutcome(run=run, findings=findings)


def _execute(
    target: ValidationTarget,
    checks: Sequence[tuple[str, Requirement]],
    *,
    planned_count: int,
    max_tool_calls: int,
    observer: CheckObserver | None,
) -> tuple[list[CheckResult], list[Finding]]:
    results: list[CheckResult] = []
    findings: list[Finding] = []
    tool_calls = 0
    for position, (check_id, requirement) in enumerate(checks):
        if position >= planned_count:
            result = _skipped(
                check_id,
                requirement.id,
                f"Skipped because MAX_PLAN_CHECKS={planned_count} was reached.",
            )
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
