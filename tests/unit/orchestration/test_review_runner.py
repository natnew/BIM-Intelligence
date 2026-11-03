"""The deterministic IDS review run (ADR-015 §4, ADR-017 §4, ADR-018; AC-02, AC-08, AC-12).

A run pins one immutable model version, executes every confirmed check against it under the
session's lock, records a ``CheckResult`` per check and publishes ``run.json`` and
``findings.json`` together. Nothing here talks to a network or a language model.
"""

from __future__ import annotations

import hashlib
import socket
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import ifctester.ids
import pytest

from bim_intelligence.bim import ingest_model
from bim_intelligence.config import Settings
from bim_intelligence.llm.client import FakeClient, RecordingClient, ReplayClient
from bim_intelligence.orchestration import NoExecutableChecksError, ReviewOutcome, run_review
from bim_intelligence.requirements import import_ids_document
from bim_intelligence.schemas import CheckResult, SelectedCheck, findings_to_json
from bim_intelligence.store import (
    ArtefactNotFoundError,
    ModelLockedError,
    ModelVersionMismatchError,
    SessionStore,
)
from fixtures.make_minimal_ifc import GLOBAL_IDS, SPEC_FIRE_RATING
from support.api import FIXTURE_BYTES
from support.ids import (
    ENTITY_WALL,
    FIXTURE_IDS_BYTES,
    REQUIRE_FIRE_RATING,
    ids_document,
    specification,
)
from support.store import tree_digest

MAX_BYTES = 1 << 20
FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()
IDS_SHA256 = hashlib.sha256(FIXTURE_IDS_BYTES).hexdigest()
START = datetime(2026, 10, 29, 9, 0, tzinfo=timezone.utc)


class _Clock:
    """Monotonic test clock: every call advances by one second."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> datetime:
        self.calls += 1
        return START + timedelta(seconds=self.calls)


@pytest.fixture
def clock() -> _Clock:
    return _Clock()


@pytest.fixture
def store(tmp_path: Path, clock: _Clock) -> SessionStore:
    return SessionStore(tmp_path / "sessions", clock=clock)


@pytest.fixture
def session_id(store: SessionStore) -> str:
    return store.create().id


@pytest.fixture
def ready_session(store: SessionStore, session_id: str) -> str:
    ingest_model(store, session_id, [FIXTURE_BYTES], max_bytes=MAX_BYTES)
    import_ids_document(store, session_id, FIXTURE_IDS_BYTES, max_bytes=MAX_BYTES)
    return session_id


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A review must never open a socket: no LLM, no telemetry, no schema download."""

    def refuse(self: socket.socket, *args: Any, **kwargs: Any) -> None:
        raise AssertionError(f"network access attempted: {args}")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    yield


# -- the happy path -----------------------------------------------------------------------


def test_review_executes_both_checks_and_records_two_findings(
    store: SessionStore, ready_session: str
) -> None:
    outcome = run_review(store, ready_session)
    run = outcome.run
    assert run.session_id == ready_session
    assert run.status == "completed"
    assert run.plan_source == "default"
    assert len(run.plan.checks) == 2
    assert [r.status for r in run.check_results] == ["failed", "failed"]
    assert [r.requirement_id for r in run.check_results] == ["REQ-001", "REQ-002"]
    assert [r.applicable_count for r in run.check_results] == [2, 3]
    assert len(outcome.findings) == 2
    assert {f.elements[0].global_id for f in outcome.findings} == {
        GLOBAL_IDS["W-002"],
        GLOBAL_IDS["W-003"],
    }
    assert sorted(run.finding_ids) == sorted(f.id for f in outcome.findings)
    assert run.finished_at is not None and run.finished_at > run.created_at
    assert run.provenance is not None
    assert run.provenance.ai_planning_requested is False
    assert run.provenance.mode == "off"
    assert run.provenance.executed_check_ids == [r.check_id for r in run.check_results]


def test_input_manifest_pins_every_input(store: SessionStore, ready_session: str) -> None:
    outcome = run_review(store, ready_session)
    manifest = outcome.run.input_manifest
    requirements = store.read_requirements(ready_session)
    assert manifest.model_hash == FIXTURE_SHA256
    assert manifest.ids_hashes == [IDS_SHA256]
    assert manifest.requirement_revisions == {"REQ-001": 1, "REQ-002": 1}
    assert manifest.rule_versions == {r.check.rule_id: r.check.rule_version for r in requirements}
    assert f"ids:{SPEC_FIRE_RATING}" in manifest.rule_versions


def test_run_and_findings_are_persisted_together(store: SessionStore, ready_session: str) -> None:
    outcome = run_review(store, ready_session)
    assert store.list_runs(ready_session) == [outcome.run.id]
    assert store.read_run(ready_session, outcome.run.id) == outcome.run
    assert store.read_findings(ready_session, outcome.run.id) == outcome.findings


def test_timestamps_come_from_the_store_clock(store: SessionStore, ready_session: str) -> None:
    outcome = run_review(store, ready_session)
    assert outcome.run.created_at > START
    assert outcome.run.finished_at is not None
    assert (outcome.run.finished_at - START).total_seconds() < 60


# -- determinism and read-only guarantees (AC-02, AC-08) -------------------------------------


def test_two_runs_produce_byte_identical_findings_json(
    store: SessionStore, ready_session: str
) -> None:
    first = run_review(store, ready_session)
    second = run_review(store, ready_session)
    assert first.run.id != second.run.id
    assert findings_to_json(first.findings) == findings_to_json(second.findings)
    volatile = {"id", "created_at", "finished_at"}
    first_json = first.run.model_dump(mode="json", exclude=volatile)
    second_json = second.run.model_dump(mode="json", exclude=volatile)
    assert first_json == second_json


def test_model_version_directory_is_byte_identical_after_a_run(
    store: SessionStore, ready_session: str
) -> None:
    version = store.active_model(ready_session)
    before = tree_digest(version.directory)
    run_review(store, ready_session)
    assert tree_digest(version.directory) == before
    assert version.read_bytes() == FIXTURE_BYTES


# -- preconditions ------------------------------------------------------------------------


def test_review_without_a_model_is_refused(store: SessionStore, session_id: str) -> None:
    import_ids_document(store, session_id, FIXTURE_IDS_BYTES, max_bytes=MAX_BYTES)
    with pytest.raises(ArtefactNotFoundError):
        run_review(store, session_id)
    assert store.list_runs(session_id) == []


def test_review_without_executable_requirements_is_refused(
    store: SessionStore, session_id: str
) -> None:
    ingest_model(store, session_id, [FIXTURE_BYTES], max_bytes=MAX_BYTES)
    with pytest.raises(NoExecutableChecksError):
        run_review(store, session_id)
    assert store.list_runs(session_id) == []


def test_review_pinned_to_a_stale_version_is_refused(
    store: SessionStore, ready_session: str
) -> None:
    with pytest.raises(ModelVersionMismatchError) as excinfo:
        run_review(store, ready_session, pinned_model_hash="0" * 64)
    assert excinfo.value.active == FIXTURE_SHA256
    assert store.list_runs(ready_session) == []


def test_review_pinned_to_the_active_version_runs(store: SessionStore, ready_session: str) -> None:
    outcome = run_review(store, ready_session, pinned_model_hash=FIXTURE_SHA256)
    assert outcome.run.input_manifest.model_hash == FIXTURE_SHA256


def test_strict_ai_review_rejects_an_unavailable_planner_without_publishing(
    store: SessionStore, ready_session: str
) -> None:
    from bim_intelligence.orchestration import AIReviewRequiredError

    with pytest.raises(AIReviewRequiredError) as exc_info:
        run_review(
            store,
            ready_session,
            objective="Review the confirmed requirements.",
            ai_required=True,
            client=None,
        )

    assert exc_info.value.reason_code == "provider_unavailable"
    assert exc_info.value.provider_request_attempted is False
    assert store.list_runs(ready_session) == []


def test_explicit_deterministic_continuation_does_not_call_the_client(
    store: SessionStore, ready_session: str
) -> None:
    fake = FakeClient([])
    outcome = run_review(
        store,
        ready_session,
        objective="Review the confirmed requirements.",
        ai_required=True,
        continue_without_ai=True,
        client=fake,
    )

    assert fake.calls == 0
    assert outcome.run.plan_source == "default"
    assert outcome.run.provenance is not None
    assert outcome.run.provenance.outcome == "continued_without_ai"
    assert outcome.run.provenance.fallback_reason == "user_selected_continue_without_ai"
    assert outcome.run.provenance.deterministic_fallback is True


def test_replay_run_persists_replay_mode_and_retrieves_the_same_provenance(
    store: SessionStore, ready_session: str, tmp_path: Path
) -> None:
    check_id = store.read_requirements(ready_session)[0].check.id
    response: dict[str, object] = {
        "checks": [{"check_id": check_id, "reason": "Matches the selected objective."}]
    }
    recordings = tmp_path / "recordings"
    recorder = RecordingClient(
        FakeClient([response]),
        recordings,
    )
    run_review(
        store,
        ready_session,
        objective="Review the first confirmed check.",
        ai_required=True,
        client=recorder,
    )

    replay = ReplayClient(recordings)
    outcome = run_review(
        store,
        ready_session,
        settings=Settings(llm_mode="replay", llm_recordings_dir=recordings),
        objective="Review the first confirmed check.",
        ai_required=True,
        client=replay,
    )
    fetched = store.read_run(ready_session, outcome.run.id)

    assert fetched.provenance is not None
    assert fetched.provenance.mode == "replay"
    assert fetched.provenance.provider_request_attempted is False
    assert fetched.provenance.model == "fake-model"
    assert fetched.provenance.outcome == "accepted"
    assert fetched == outcome.run


def test_selected_check_scope_cannot_run_unselected_checks(
    store: SessionStore, ready_session: str
) -> None:
    requirements = store.read_requirements(ready_session)
    selected = requirements[1]
    outcome = run_review(
        store,
        ready_session,
        selected_checks=[
            SelectedCheck(
                check_id=selected.check.id,
                requirement_id=selected.id,
                requirement_revision=selected.revision,
            )
        ],
    )

    assert [result.check_id for result in outcome.run.check_results] == [selected.check.id]
    assert outcome.run.provenance is not None
    assert outcome.run.provenance.selected_check_ids == [selected.check.id]
    assert outcome.run.provenance.executed_check_ids == [selected.check.id]
    assert outcome.run.input_manifest.requirement_revisions == {selected.id: selected.revision}


@pytest.mark.parametrize(
    ("requirement_id", "check_id", "revision"),
    [
        ("REQ-UNKNOWN", "unknown", 1),
        ("REQ-001", "stale-check", 1),
        ("REQ-001", "current-check", 99),
    ],
)
def test_selected_check_scope_rejects_unknown_or_stale_selections(
    store: SessionStore,
    ready_session: str,
    requirement_id: str,
    check_id: str,
    revision: int,
) -> None:
    from bim_intelligence.orchestration import ReviewScopeError

    with pytest.raises(ReviewScopeError):
        run_review(
            store,
            ready_session,
            selected_checks=[
                SelectedCheck(
                    check_id=check_id,
                    requirement_id=requirement_id,
                    requirement_revision=revision,
                )
            ],
        )


def test_selected_check_scope_rejects_an_unconfirmed_requirement(
    store: SessionStore, ready_session: str
) -> None:
    from bim_intelligence.orchestration import ReviewScopeError

    requirements = store.read_requirements(ready_session)
    unconfirmed = requirements[0].model_copy(
        update={"status": "proposed", "confirmed_revision": None, "confirmed_by": None}
    )
    with store.lock_model(ready_session) as lock:
        store.write_requirements(lock, [unconfirmed, *requirements[1:]])

    with pytest.raises(ReviewScopeError):
        run_review(
            store,
            ready_session,
            selected_checks=[
                SelectedCheck(
                    check_id=unconfirmed.check.id,
                    requirement_id=unconfirmed.id,
                    requirement_revision=unconfirmed.revision,
                )
            ],
        )


# -- version consistency while validating (ADR-017 §4, AC-12) -------------------------------


def test_upload_during_a_run_is_refused_and_the_run_keeps_its_version(
    store: SessionStore, ready_session: str
) -> None:
    replacement = FIXTURE_BYTES.replace(b"'Minimal Project'", b"'Replaced Project'")
    assert replacement != FIXTURE_BYTES
    attempts: list[type[BaseException]] = []

    def try_to_replace_the_model(result: CheckResult) -> None:
        try:
            ingest_model(store, ready_session, [replacement], max_bytes=MAX_BYTES)
        except ModelLockedError as exc:
            attempts.append(type(exc))

    outcome = run_review(store, ready_session, observer=try_to_replace_the_model)
    assert attempts == [ModelLockedError, ModelLockedError]
    assert outcome.run.input_manifest.model_hash == FIXTURE_SHA256
    assert store.active_model(ready_session).sha256 == FIXTURE_SHA256
    assert store.list_model_versions(ready_session) == [FIXTURE_SHA256]


def test_second_concurrent_run_is_refused(store: SessionStore, ready_session: str) -> None:
    nested: list[type[BaseException]] = []

    def start_another_run(result: CheckResult) -> None:
        try:
            run_review(store, ready_session)
        except ModelLockedError as exc:
            nested.append(type(exc))

    outcome = run_review(store, ready_session, observer=start_another_run)
    assert nested == [ModelLockedError, ModelLockedError]
    assert outcome.run.status == "completed"
    assert store.list_runs(ready_session) == [outcome.run.id]


def test_run_after_a_reupload_validates_the_new_active_version(
    store: SessionStore, ready_session: str
) -> None:
    first = run_review(store, ready_session)
    replacement = FIXTURE_BYTES.replace(b"'Minimal Project'", b"'Replaced Project'")
    ingest_model(store, ready_session, [replacement], max_bytes=MAX_BYTES)
    second = run_review(store, ready_session)
    assert first.run.input_manifest.model_hash == FIXTURE_SHA256
    assert second.run.input_manifest.model_hash == hashlib.sha256(replacement).hexdigest()
    # The superseded version is retained, so the first run's evidence remains resolvable.
    assert store.model_version(ready_session, FIXTURE_SHA256).is_complete


# -- degraded outcomes --------------------------------------------------------------------


def test_engine_failure_in_one_check_leaves_the_run_partial_and_the_other_check_intact(
    store: SessionStore, ready_session: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = ifctester.ids.Specification.validate

    def fail_fire_rating(self: Any, *args: Any, **kwargs: Any) -> None:
        if self.name == SPEC_FIRE_RATING:
            raise RuntimeError("injected engine failure")
        original(self, *args, **kwargs)

    monkeypatch.setattr(ifctester.ids.Specification, "validate", fail_fire_rating)
    outcome: ReviewOutcome = run_review(store, ready_session)
    assert outcome.run.status == "partial"
    by_requirement = {r.requirement_id: r for r in outcome.run.check_results}
    assert by_requirement["REQ-001"].status == "error"
    assert any("injected engine failure" in d for d in by_requirement["REQ-001"].diagnostics)
    assert by_requirement["REQ-002"].status == "failed"
    assert len(outcome.findings) == 1
    assert outcome.findings[0].elements[0].global_id == GLOBAL_IDS["W-003"]


def test_observer_sees_each_check_result_in_plan_order(
    store: SessionStore, ready_session: str
) -> None:
    seen: list[str] = []
    outcome = run_review(store, ready_session, observer=lambda r: seen.append(r.requirement_id))
    assert seen == [r.requirement_id for r in outcome.run.check_results] == ["REQ-001", "REQ-002"]


def _import_cap_checks(store: SessionStore, session_id: str) -> None:
    document = ids_document(
        *(
            specification(f"Cap check {index}", ENTITY_WALL, REQUIRE_FIRE_RATING)
            for index in range(3)
        )
    )
    import_ids_document(store, session_id, document, max_bytes=MAX_BYTES)


def test_plan_cap_records_unplanned_confirmed_checks_as_skipped(
    store: SessionStore, ready_session: str
) -> None:
    _import_cap_checks(store, ready_session)

    outcome = run_review(
        store,
        ready_session,
        settings=Settings(max_plan_checks=2, max_tool_calls_per_run=12),
    )

    assert len(outcome.run.plan.checks) == 2
    assert len(outcome.run.check_results) == 5
    assert [result.status for result in outcome.run.check_results[:2]] == ["failed", "failed"]
    assert [result.status for result in outcome.run.check_results[2:]] == ["skipped"] * 3
    assert all(
        "MAX_PLAN_CHECKS" in result.diagnostics[0] for result in outcome.run.check_results[2:]
    )
    assert outcome.run.status == "partial"


def test_tool_call_cap_records_remaining_planned_checks_as_skipped(
    store: SessionStore, ready_session: str
) -> None:
    _import_cap_checks(store, ready_session)

    outcome = run_review(
        store,
        ready_session,
        settings=Settings(max_plan_checks=10, max_tool_calls_per_run=1),
    )

    assert len(outcome.run.plan.checks) == 5
    assert [result.status for result in outcome.run.check_results] == [
        "failed",
        "skipped",
        "skipped",
        "skipped",
        "skipped",
    ]
    assert all(
        "MAX_TOOL_CALLS_PER_RUN" in result.diagnostics[0]
        for result in outcome.run.check_results[1:]
    )
    assert outcome.run.status == "partial"
