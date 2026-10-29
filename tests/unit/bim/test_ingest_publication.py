"""Publication consistency of ``ingest_model`` under failure and concurrency (ADR-017).

Every test asserts the same invariant from different angles: whatever happens during an
upload, the session's active IFC bytes, index, summary and ``model_hash`` all describe one
version. Failures are injected at each publication step; concurrency is driven with explicit
barriers so the interleaving is deterministic rather than timing-dependent.
"""

from __future__ import annotations

import hashlib
import os
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from bim_intelligence.bim import IfcLoadError, ingest_model, load_index, load_summary
from bim_intelligence.bim import ingest as ingest_module
from bim_intelligence.bim.indexer import build_index as real_build_index
from bim_intelligence.store import (
    MODEL_FILE,
    MODEL_INDEX_FILE,
    MODEL_SUMMARY_FILE,
    MODELS_DIR,
    SESSION_FILE,
    STAGING_PREFIX,
    ModelLockedError,
    SessionStore,
    StorageError,
)
from bim_intelligence.store import session_store as store_module
from fixtures.make_minimal_ifc import IFC_PATH
from support.store import tree_digest

BYTES_A = IFC_PATH.read_bytes()
BYTES_B = BYTES_A + b"\n"  # a different hash, still a valid IFC
HASH_A = hashlib.sha256(BYTES_A).hexdigest()
HASH_B = hashlib.sha256(BYTES_B).hexdigest()
MAX_BYTES = 10**6
BARRIER_TIMEOUT = 30.0


@pytest.fixture
def store(tmp_path: Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions")


@pytest.fixture
def loaded(store: SessionStore) -> str:
    session = store.create()
    ingest_model(store, session.id, [BYTES_A], max_bytes=MAX_BYTES)
    return session.id


def assert_consistent(
    store: SessionStore, session_id: str, expected_hash: str, *, in_flight: bool = False
) -> None:
    """The committed state names exactly one version, and every artefact belongs to it.

    ``in_flight`` allows a staging directory to exist (an upload is legitimately in progress).
    """
    session = store.get(session_id)
    version = store.active_model(session_id)
    data = version.read_bytes()
    summary = load_summary(version)
    index = load_index(version)
    observed = {
        "session.model_hash": session.model_hash,
        "version": version.sha256,
        "sha256(bytes)": hashlib.sha256(data).hexdigest(),
        "summary.model_hash": summary.model_hash,
        "index.summary.model_hash": index.summary.model_hash,
    }
    assert set(observed.values()) == {expected_hash}, observed
    assert session.status == "model_ready"
    if not in_flight:
        assert store.staging_directories(session_id) == []


def session_snapshot(store: SessionStore, session_id: str) -> dict[str, str]:
    return tree_digest(store.root / session_id)


# -- failure injection --------------------------------------------------------------------


def _reupload_fails(
    store: SessionStore, session_id: str, exc_type: type[BaseException], match: str
) -> None:
    before = session_snapshot(store, session_id)
    with pytest.raises(exc_type, match=match):
        ingest_model(store, session_id, [BYTES_B], max_bytes=MAX_BYTES)
    assert_consistent(store, session_id, HASH_A)
    assert session_snapshot(store, session_id) == before, "a rejected upload changes nothing"
    assert store.list_model_versions(session_id) == [HASH_A]


def test_failure_before_publication_changes_nothing(
    store: SessionStore, loaded: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("indexer crashed")

    monkeypatch.setattr(ingest_module, "build_index", explode)
    _reupload_fails(store, loaded, RuntimeError, "indexer crashed")


@pytest.mark.parametrize("artefact", [MODEL_INDEX_FILE, MODEL_SUMMARY_FILE])
def test_failure_writing_a_derived_artefact_changes_nothing(
    store: SessionStore, loaded: str, monkeypatch: pytest.MonkeyPatch, artefact: str
) -> None:
    real_write_json = store_module.StagedModel.write_json

    def failing_write_json(self: store_module.StagedModel, name: str, value: Any) -> Path:
        if name == artefact:
            raise StorageError(f"disk full while writing {name}")
        return real_write_json(self, name, value)

    monkeypatch.setattr(store_module.StagedModel, "write_json", failing_write_json)
    _reupload_fails(store, loaded, StorageError, "disk full")


def test_failure_publishing_the_version_directory_changes_nothing(
    store: SessionStore, loaded: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing_replace(src: Path, dst: Path) -> None:
        if src.name.startswith(STAGING_PREFIX):
            raise OSError("rename refused")
        os.replace(src, dst)

    monkeypatch.setattr(store_module, "_replace", failing_replace)
    _reupload_fails(store, loaded, StorageError, "publish the staged")


def test_failure_activating_the_version_leaves_the_old_one_active(
    store: SessionStore, loaded: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The version directory is committed but the pointer swap fails: old version stays whole."""

    def failing_replace(src: Path, dst: Path) -> None:
        if dst.name == SESSION_FILE:
            raise OSError("cannot write session record")
        os.replace(src, dst)

    monkeypatch.setattr(store_module, "_replace", failing_replace)
    before = session_snapshot(store, loaded)
    with pytest.raises(StorageError, match=r"session\.json"):
        ingest_model(store, loaded, [BYTES_B], max_bytes=MAX_BYTES)
    assert_consistent(store, loaded, HASH_A)
    # The only difference is a complete, inactive version B: never partial, never served.
    after = session_snapshot(store, loaded)
    new_files = {k: v for k, v in after.items() if k not in before}
    assert {k for k in after if k in before} == set(before)
    assert all(before[k] == after[k] for k in before), "existing files are untouched"
    assert set(new_files) == {
        f"{MODELS_DIR}/{HASH_B}/{MODEL_FILE}",
        f"{MODELS_DIR}/{HASH_B}/{MODEL_INDEX_FILE}",
        f"{MODELS_DIR}/{HASH_B}/{MODEL_SUMMARY_FILE}",
    }
    assert sorted(store.list_model_versions(loaded)) == sorted([HASH_A, HASH_B])
    monkeypatch.undo()
    with store.lock_model(loaded) as lock:
        assert store.prune_model_versions(lock) == [HASH_B]


def test_rejected_upload_leaves_the_directory_byte_identical(
    store: SessionStore, loaded: str
) -> None:
    before = session_snapshot(store, loaded)
    with pytest.raises(IfcLoadError):
        ingest_model(store, loaded, [b"not an ifc"], max_bytes=MAX_BYTES)
    assert session_snapshot(store, loaded) == before
    assert_consistent(store, loaded, HASH_A)


# -- concurrency --------------------------------------------------------------------------


def _blocking_indexer(
    monkeypatch: pytest.MonkeyPatch, entered: threading.Event, proceed: threading.Event
) -> None:
    """Make the first ``build_index`` call signal ``entered`` and wait for ``proceed``."""
    first_call = threading.Event()

    def gated_build_index(*args: Any, **kwargs: Any) -> Any:
        if not first_call.is_set():
            first_call.set()
            entered.set()
            assert proceed.wait(BARRIER_TIMEOUT), "test barrier timed out"
        return real_build_index(*args, **kwargs)

    monkeypatch.setattr(ingest_module, "build_index", gated_build_index)


def test_second_concurrent_upload_is_refused_and_the_first_publishes_cleanly(
    store: SessionStore, loaded: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered, proceed = threading.Event(), threading.Event()
    _blocking_indexer(monkeypatch, entered, proceed)
    errors: list[BaseException] = []

    def first_upload() -> None:
        try:
            ingest_model(store, loaded, [BYTES_B], max_bytes=MAX_BYTES)
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=first_upload)
    thread.start()
    try:
        assert entered.wait(BARRIER_TIMEOUT), "first upload never reached indexing"
        assert len(store.staging_directories(loaded)) == 1
        assert_consistent(store, loaded, HASH_A, in_flight=True)
        with pytest.raises(ModelLockedError, match=loaded):
            ingest_model(SessionStore(store.root), loaded, [BYTES_A], max_bytes=MAX_BYTES)
        assert_consistent(store, loaded, HASH_A, in_flight=True)
    finally:
        proceed.set()
        thread.join(timeout=BARRIER_TIMEOUT)
    assert not thread.is_alive()
    assert errors == []
    assert_consistent(store, loaded, HASH_B)
    assert sorted(store.list_model_versions(loaded)) == sorted([HASH_A, HASH_B])


def test_readers_never_observe_a_mixed_version_during_replacement(
    store: SessionStore, loaded: str
) -> None:
    stop = threading.Event()
    failures: list[BaseException] = []
    reads = [0]
    counter_lock = threading.Lock()

    def reader() -> None:
        own_store = SessionStore(store.root)
        while not stop.is_set():
            try:
                version = own_store.active_model(loaded)
                data = version.read_bytes()
                summary = load_summary(version)
                index = load_index(version)
                hashes = {
                    version.sha256,
                    hashlib.sha256(data).hexdigest(),
                    summary.model_hash,
                    index.summary.model_hash,
                }
                assert len(hashes) == 1, hashes
                assert hashes <= {HASH_A, HASH_B}
                with counter_lock:
                    reads[0] += 1
            except BaseException as exc:
                failures.append(exc)
                return

    threads = [threading.Thread(target=reader) for _ in range(4)]
    for thread in threads:
        thread.start()
    try:
        replacements = [BYTES_B, BYTES_A, BYTES_B, BYTES_A, BYTES_B, BYTES_A, BYTES_B]
        for data in replacements:
            ingest_model(store, loaded, [data], max_bytes=MAX_BYTES)
    finally:
        stop.set()
        for thread in threads:
            thread.join(timeout=BARRIER_TIMEOUT)
    assert failures == [], failures
    assert reads[0] > 0
    assert_consistent(store, loaded, HASH_B)


# -- recovery -----------------------------------------------------------------------------


def _abandon_staging(store: SessionStore, session_id: str) -> Path:
    directory = store.root / session_id / MODELS_DIR / f"{STAGING_PREFIX}abandoned"
    directory.mkdir(parents=True)
    (directory / MODEL_FILE).write_bytes(BYTES_B[: len(BYTES_B) // 2])
    return directory


def test_restart_with_abandoned_staging_recovers_and_serves_the_committed_version(
    store: SessionStore, loaded: str
) -> None:
    abandoned = _abandon_staging(store, loaded)
    restarted = SessionStore(store.root)  # a new process would see the same directory
    assert restarted.active_model(loaded).sha256 == HASH_A, "staging is invisible to readers"
    assert restarted.sweep_all_staging() == 1
    assert not abandoned.exists()
    assert_consistent(restarted, loaded, HASH_A)


def test_next_upload_discards_abandoned_staging_before_publishing(
    store: SessionStore, loaded: str
) -> None:
    abandoned = _abandon_staging(store, loaded)
    ingest_model(SessionStore(store.root), loaded, [BYTES_B], max_bytes=MAX_BYTES)
    assert not abandoned.exists()
    assert_consistent(store, loaded, HASH_B)


# -- chunking -----------------------------------------------------------------------------


def _chunks(data: bytes, size: int) -> Iterator[bytes]:
    for i in range(0, len(data), size):
        yield data[i : i + size]


def test_chunked_upload_hashes_identically(store: SessionStore) -> None:
    session = store.create()
    ingest_model(store, session.id, _chunks(BYTES_A, 777), max_bytes=MAX_BYTES)
    assert_consistent(store, session.id, HASH_A)
