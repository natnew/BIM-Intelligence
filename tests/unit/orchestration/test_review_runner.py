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
from bim_intelligence.orchestration import NoExecutableChecksError, ReviewOutcome, run_review
from bim_intelligence.requirements import import_ids_document
from bim_intelligence.schemas import CheckResult, findings_to_json
from bim_intelligence.store import (
    ArtefactNotFoundError,
    ModelLockedError,
    ModelVersionMismatchError,
    SessionStore,
)
from fixtures.make_minimal_ifc import GLOBAL_IDS, SPEC_FIRE_RATING
from support.api import FIXTURE_BYTES
from support.ids import FIXTURE_IDS_BYTES
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
