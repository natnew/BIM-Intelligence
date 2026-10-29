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
5. Publish ``run.json`` and ``findings.json`` together. The run is ``completed`` when every
   check executed, ``partial`` when any check ended in ``error``.

The run is synchronous: the caller receives the terminal ``ReviewRun``. No network access, no
language model, no background task (ADR-013 remains the design for longer runs).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from bim_intelligence.bim import load_index
from bim_intelligence.orchestration.default_plan import default_plan
from bim_intelligence.schemas import (
    CheckResult,
    Finding,
    InputManifest,
    Requirement,
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


class NoExecutableChecksError(Exception):
    """The session has no confirmed requirement to run (ARCHITECTURE §14: 409)."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"Session {session_id} has no confirmed requirements to review; upload an IDS "
            "document first."
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
) -> ReviewOutcome:
    """Run the default plan against the session's active model and publish the result.

    ``pinned_model_hash`` is the version the caller expects to be validated; a different active
    version is refused. ``observer`` is called with each ``CheckResult`` as it is produced (used
    for logging and, in tests, to exercise the lock while the run is in progress).
    """
    with store.lock_model(session_id):
        version = store.active_model(session_id)
        if pinned_model_hash is not None and pinned_model_hash != version.sha256:
            raise ModelVersionMismatchError(session_id, pinned_model_hash, version.sha256)
        plan, by_check = default_plan(store.read_requirements(session_id))
        if not plan.checks:
            raise NoExecutableChecksError(session_id)
        attributed = list(by_check.values())
        manifest = _manifest(store, session_id, version, attributed)

        created_at = store.now()
        with ValidationTarget.open(version.path_for(MODEL_FILE), load_index(version)) as target:
            results, findings = _execute(target, attributed, observer)
        findings = sort_findings(findings)

        run = ReviewRun(
            id=store.new_id(),
            session_id=session_id,
            status=_run_status(results),
            plan=plan,
            plan_source="default",
            check_results=results,
            input_manifest=manifest,
            created_at=created_at,
            finished_at=store.now(),
        )
        store.publish_run(run, findings)
    return ReviewOutcome(run=run, findings=findings)


def _execute(
    target: ValidationTarget, requirements: Sequence[Requirement], observer: CheckObserver | None
) -> tuple[list[CheckResult], list[Finding]]:
    results: list[CheckResult] = []
    findings: list[Finding] = []
    for requirement in requirements:
        outcome = target.run(requirement.check, requirement_id=requirement.id)
        results.append(outcome.result)
        findings.extend(outcome.findings)
        if observer is not None:
            observer(outcome.result)
    return results, findings


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
    return "partial" if any(result.status == "error" for result in results) else "completed"
