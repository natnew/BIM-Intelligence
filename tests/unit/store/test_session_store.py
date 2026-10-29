"""SessionStore: UUID-scoped directories, content-addressed model versions (ADR-006, ADR-017).

AC-02: the stored IFC's SHA-256 equals the uploaded bytes. The tests also pin the path-safety
properties ARCHITECTURE §13 relies on — no client-controlled path component ever reaches the
file system — and the publication invariant of ADR-017: a version directory exists complete or
not at all, and ``session.json`` only ever points at a complete one.
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

from bim_intelligence.schemas import SESSION_ID_PATTERN
from bim_intelligence.store import (
    LOCK_FILE,
    MODEL_FILE,
    MODEL_INDEX_FILE,
    MODEL_SUMMARY_FILE,
    MODELS_DIR,
    SESSION_FILE,
    STAGING_PREFIX,
    ArtefactNotFoundError,
    IncompleteModelVersionError,
    InvalidSessionIdError,
    ModelLockedError,
    SessionNotFoundError,
    SessionStore,
    StorageError,
    UploadTooLargeError,
)
from bim_intelligence.store import session_store as store_module
from fixtures.make_minimal_ifc import IFC_PATH
from support.store import fake_index, fake_summary, publish_version, sha256_of

FIXED_NOW = datetime(2026, 10, 28, 9, 0, tzinfo=timezone.utc)
UNKNOWN_ID = "0f1b7a2e-5c3d-4e8f-9a1b-2c3d4e5f6a7b"


@pytest.fixture
def store(tmp_path: Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions", clock=lambda: FIXED_NOW)


def _names(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir())


class TestSessions:
    def test_create_makes_a_uuid4_directory_with_a_session_record(
        self, store: SessionStore
    ) -> None:
        session = store.create()
        assert re.fullmatch(SESSION_ID_PATTERN, session.id)
        assert session.status == "created"
        assert session.created_at == FIXED_NOW
        assert (store.root / session.id).is_dir()
        assert (store.root / session.id / SESSION_FILE).is_file()

    def test_get_round_trips_the_record(self, store: SessionStore) -> None:
        created = store.create()
        assert store.get(created.id) == created

    def test_sessions_are_distinct_and_isolated(self, store: SessionStore) -> None:
        a, b = store.create(), store.create()
        assert a.id != b.id
        publish_version(store, a.id, b"ISO-10303-21;")
        assert store.has_model(a.id) is True
        assert store.has_model(b.id) is False
        assert store.get(b.id).model_hash is None

    def test_session_ids_lists_only_real_sessions(self, store: SessionStore) -> None:
        assert store.session_ids() == []
        a, b = store.create(), store.create()
        (store.root / UNKNOWN_ID).mkdir()
        (store.root / "not-a-session").mkdir()
        assert store.session_ids() == sorted([a.id, b.id])

    def test_unknown_session_raises(self, store: SessionStore) -> None:
        with pytest.raises(SessionNotFoundError, match=UNKNOWN_ID):
            store.get(UNKNOWN_ID)
        with pytest.raises(SessionNotFoundError):
            store.active_model(UNKNOWN_ID)
        with pytest.raises(SessionNotFoundError):
            store.lock_model(UNKNOWN_ID)

    @pytest.mark.parametrize(
        "bad_id",
        ["..", "../..", "x", "0F1B7A2E-5C3D-4E8F-9A1B-2C3D4E5F6A7B", UNKNOWN_ID + "/..", ""],
    )
    def test_malformed_ids_never_touch_the_file_system(
        self, store: SessionStore, bad_id: str
    ) -> None:
        with pytest.raises(InvalidSessionIdError):
            store.get(bad_id)
        with pytest.raises(InvalidSessionIdError):
            store.session_dir(bad_id)
        with pytest.raises(InvalidSessionIdError):
            store.lock_model(bad_id)
        assert not store.root.exists() or list(store.root.iterdir()) == []

    def test_a_directory_without_a_record_is_not_a_session(self, store: SessionStore) -> None:
        (store.root / UNKNOWN_ID).mkdir(parents=True)
        with pytest.raises(SessionNotFoundError):
            store.get(UNKNOWN_ID)

    def test_corrupt_record_is_a_storage_error(self, store: SessionStore) -> None:
        session = store.create()
        (store.root / session.id / SESSION_FILE).write_text("{not json", encoding="utf-8")
        with pytest.raises(StorageError):
            store.get(session.id)


class TestPaths:
    def test_session_dir_stays_inside_the_store_root(self, store: SessionStore) -> None:
        session = store.create()
        path = store.session_dir(session.id).resolve()
        assert path.is_relative_to(store.root.resolve())
        assert path.name == session.id

    def test_only_fixed_model_artefact_names_are_addressable(self, store: SessionStore) -> None:
        session = store.create()
        version = publish_version(store, session.id, b"bytes")
        for name in (MODEL_FILE, MODEL_INDEX_FILE, MODEL_SUMMARY_FILE):
            path = version.path_for(name)
            assert path.parent == store.root / session.id / MODELS_DIR / version.sha256
            assert path.name == name
        for name in ("../model.ifc", "model.ifc/..", "other.ifc", "", "C:/windows/x", SESSION_FILE):
            with pytest.raises(ValueError):
                version.path_for(name)

    def test_model_versions_are_addressed_by_sha256_only(self, store: SessionStore) -> None:
        session = store.create()
        for bad in ("abc", "../" + "a" * 61, "A" * 64, ""):
            with pytest.raises(ValueError):
                store.model_version(session.id, bad)


class TestStaging:
    def test_staged_version_is_private_until_commit(self, store: SessionStore) -> None:
        session = store.create()
        data = IFC_PATH.read_bytes()
        with store.lock_model(session.id) as lock:
            with store.stage_model(lock, max_bytes=len(data)) as staged:
                for i in range(0, len(data), 1000):
                    staged.write(data[i : i + 1000])
                path = staged.seal()
                assert path.read_bytes() == data
                assert staged.directory.name.startswith(STAGING_PREFIX)
                assert staged.directory.parent == store.root / session.id / MODELS_DIR
                assert staged.sha256 == sha256_of(data)
                assert staged.size == len(data)
                assert store.has_model(session.id) is False
                assert store.list_model_versions(session.id) == []
                staged.write_json(MODEL_SUMMARY_FILE, fake_summary(staged.sha256))
                staged.write_json(MODEL_INDEX_FILE, fake_index(staged.sha256))
                assert store.has_model(session.id) is False, "not active until set_model"
                version = staged.commit()
            assert version.is_complete
            assert version.directory == store.root / session.id / MODELS_DIR / version.sha256
            assert store.list_model_versions(session.id) == [version.sha256]
            assert store.get(session.id).model_hash is None, "committed is not active"
            store.set_model(lock, version.sha256)
        assert store.get(session.id).model_hash == version.sha256
        assert store.get(session.id).status == "model_ready"
        assert store.read_model_bytes(session.id) == data
        assert store.staging_directories(session.id) == []

    def test_leaving_without_commit_removes_the_staging_directory(
        self, store: SessionStore
    ) -> None:
        session = store.create()
        with store.lock_model(session.id) as lock, store.stage_model(lock, max_bytes=100) as s:
            s.write(b"partial")
            assert s.size == 7
        assert _names(store.root / session.id) == [LOCK_FILE, MODELS_DIR, SESSION_FILE]
        assert _names(store.root / session.id / MODELS_DIR) == []

    def test_exception_inside_staging_keeps_the_previous_version(self, store: SessionStore) -> None:
        session = store.create()
        original = publish_version(store, session.id, b"first")
        with (
            pytest.raises(RuntimeError),
            store.lock_model(session.id) as lock,
            store.stage_model(lock, max_bytes=100) as staged,
        ):
            staged.write(b"second")
            raise RuntimeError("validation failed downstream")
        assert store.read_model_bytes(session.id) == b"first"
        assert store.get(session.id).model_hash == original.sha256
        assert store.list_model_versions(session.id) == [original.sha256]
        assert store.staging_directories(session.id) == []

    def test_oversized_upload_is_rejected_and_leaves_nothing_behind(
        self, store: SessionStore
    ) -> None:
        session = store.create()
        with (
            pytest.raises(UploadTooLargeError),
            store.lock_model(session.id) as lock,
            store.stage_model(lock, max_bytes=50) as staged,
        ):
            for _ in range(10):
                staged.write(b"x" * 10)
        assert store.has_model(session.id) is False
        assert _names(store.root / session.id / MODELS_DIR) == []

    def test_write_after_seal_and_commit_twice_are_errors(self, store: SessionStore) -> None:
        session = store.create()
        with store.lock_model(session.id) as lock, store.stage_model(lock, max_bytes=100) as s:
            s.write(b"x")
            s.seal()
            with pytest.raises(StorageError):
                s.write(b"y")
            s.write_json(MODEL_SUMMARY_FILE, fake_summary(s.sha256))
            s.write_json(MODEL_INDEX_FILE, fake_index(s.sha256))
            s.commit()
            with pytest.raises(StorageError):
                s.commit()
            with pytest.raises(StorageError):
                s.write_json(MODEL_INDEX_FILE, {})

    def test_derived_artefacts_require_seal_and_known_names(self, store: SessionStore) -> None:
        session = store.create()
        with store.lock_model(session.id) as lock, store.stage_model(lock, max_bytes=100) as s:
            s.write(b"x")
            with pytest.raises(StorageError, match="seal"):
                s.write_json(MODEL_SUMMARY_FILE, {})
            s.seal()
            with pytest.raises(ValueError):
                s.write_json(MODEL_FILE, {})
            with pytest.raises(ValueError):
                s.write_json("../escape.json", {})
            with pytest.raises(StorageError):
                s.write_json(MODEL_SUMMARY_FILE, {"when": FIXED_NOW})
            assert not (s.directory / MODEL_SUMMARY_FILE).exists()

    def test_commit_refuses_an_incomplete_or_mismatched_version(self, store: SessionStore) -> None:
        session = store.create()
        with store.lock_model(session.id) as lock:
            with store.stage_model(lock, max_bytes=100) as s:
                s.write(b"x")
                s.seal()
                with pytest.raises(IncompleteModelVersionError, match="incomplete"):
                    s.commit()
            with store.stage_model(lock, max_bytes=100) as s:
                s.write(b"x")
                s.seal()
                s.write_json(MODEL_SUMMARY_FILE, fake_summary("0" * 64))
                s.write_json(MODEL_INDEX_FILE, fake_index(s.sha256))
                with pytest.raises(StorageError, match="not the uploaded bytes"):
                    s.commit()
            with store.stage_model(lock, max_bytes=100) as s:
                s.write(b"x")
                s.seal()
                s.write_json(MODEL_SUMMARY_FILE, {"nonsense": True})
                s.write_json(MODEL_INDEX_FILE, fake_index(s.sha256))
                with pytest.raises(StorageError, match="valid ModelSummary"):
                    s.commit()
            with store.stage_model(lock, max_bytes=100) as s:
                s.seal()
                s.write_json(MODEL_SUMMARY_FILE, fake_summary(s.sha256))
                s.write_json(MODEL_INDEX_FILE, fake_index(s.sha256))
                with pytest.raises(StorageError, match="empty"):
                    s.commit()
        assert store.list_model_versions(session.id) == []
        assert store.staging_directories(session.id) == []

    def test_identical_bytes_reuse_the_existing_version(self, store: SessionStore) -> None:
        session = store.create()
        first = publish_version(store, session.id, b"same")
        publish_version(store, session.id, b"other")
        again = publish_version(store, session.id, b"same")
        assert again.sha256 == first.sha256
        assert sorted(store.list_model_versions(session.id)) == sorted(
            [sha256_of(b"same"), sha256_of(b"other")]
        )
        assert store.get(session.id).model_hash == first.sha256
        assert store.staging_directories(session.id) == []

    def test_identical_bytes_repair_a_damaged_copy_of_the_version(
        self, store: SessionStore
    ) -> None:
        session = store.create()
        version = publish_version(store, session.id, b"same")
        version.path_for(MODEL_INDEX_FILE).unlink()
        with pytest.raises(IncompleteModelVersionError):
            store.active_model(session.id)
        repaired = publish_version(store, session.id, b"same")
        assert repaired.sha256 == version.sha256
        assert repaired.is_complete
        assert store.active_model(session.id).read_bytes() == b"same"
        assert store.staging_directories(session.id) == []

    def test_staging_requires_the_lock_to_be_held(self, store: SessionStore) -> None:
        session = store.create()
        lock = store.lock_model(session.id)
        with pytest.raises(StorageError, match="lock"):
            store.stage_model(lock, max_bytes=10)
        with pytest.raises(StorageError, match="lock"):
            store.set_model(lock, "a" * 64)
        with pytest.raises(StorageError, match="lock"):
            store.discard_staging(lock)
        with pytest.raises(StorageError, match="lock"):
            store.prune_model_versions(lock)


class TestActivation:
    def test_set_model_refuses_a_missing_or_incomplete_version(self, store: SessionStore) -> None:
        session = store.create()
        with store.lock_model(session.id) as lock:
            with pytest.raises(IncompleteModelVersionError):
                store.set_model(lock, "a" * 64)
            version = store.model_version(session.id, "b" * 64)
            version.directory.mkdir(parents=True)
            (version.directory / MODEL_FILE).write_bytes(b"x")
            with pytest.raises(IncompleteModelVersionError, match=r"model_index\.json"):
                store.set_model(lock, "b" * 64)
        assert store.get(session.id).model_hash is None
        assert store.list_model_versions(session.id) == []

    def test_set_model_records_hash_in_session_json_without_paths(
        self, store: SessionStore
    ) -> None:
        session = store.create()
        version = publish_version(store, session.id, b"x")
        record = json.loads((store.root / session.id / SESSION_FILE).read_text(encoding="utf-8"))
        assert record["model_hash"] == version.sha256
        assert record["status"] == "model_ready"
        assert "path" not in json.dumps(record)
        assert str(store.root) not in json.dumps(record)

    def test_active_model_resolves_everything_from_one_directory(self, store: SessionStore) -> None:
        session = store.create()
        publish_version(store, session.id, b"first", project_name="One")
        publish_version(store, session.id, b"second", project_name="Two")
        version = store.active_model(session.id)
        assert version.sha256 == sha256_of(b"second")
        assert version.read_bytes() == b"second"
        assert version.read_json(MODEL_SUMMARY_FILE)["model_hash"] == version.sha256
        assert version.read_json(MODEL_SUMMARY_FILE)["project_name"] == "Two"
        assert version.read_json(MODEL_INDEX_FILE)["summary"]["model_hash"] == version.sha256

    def test_superseded_versions_remain_readable_until_pruned(self, store: SessionStore) -> None:
        session = store.create()
        first = publish_version(store, session.id, b"first")
        second = publish_version(store, session.id, b"second")
        pinned = store.model_version(session.id, first.sha256)
        assert pinned.read_bytes() == b"first"
        assert pinned.read_json(MODEL_SUMMARY_FILE)["model_hash"] == first.sha256
        with store.lock_model(session.id) as lock:
            assert store.prune_model_versions(lock, keep=[first.sha256]) == []
            assert store.prune_model_versions(lock) == [first.sha256]
        assert store.list_model_versions(session.id) == [second.sha256]
        assert store.active_model(session.id).sha256 == second.sha256
        assert not pinned.is_complete

    def test_model_absent_until_activated(self, store: SessionStore) -> None:
        session = store.create()
        with pytest.raises(ArtefactNotFoundError):
            store.read_model_bytes(session.id)
        with pytest.raises(ArtefactNotFoundError):
            store.active_model(session.id)
        assert store.has_model(session.id) is False

    def test_pointer_to_a_damaged_version_is_a_storage_error(self, store: SessionStore) -> None:
        session = store.create()
        version = publish_version(store, session.id, b"x")
        version.path_for(MODEL_INDEX_FILE).unlink()
        with pytest.raises(IncompleteModelVersionError):
            store.active_model(session.id)
        with pytest.raises(StorageError):
            store.read_model_bytes(session.id)

    def test_corrupt_artefact_is_a_storage_error(self, store: SessionStore) -> None:
        session = store.create()
        version = publish_version(store, session.id, b"x")
        version.path_for(MODEL_SUMMARY_FILE).write_text("{oops", encoding="utf-8")
        with pytest.raises(StorageError, match="unreadable"):
            store.active_model(session.id).read_json(MODEL_SUMMARY_FILE)


class TestLock:
    def test_lock_is_exclusive_across_store_instances_and_threads(
        self, store: SessionStore
    ) -> None:
        session = store.create()
        other = SessionStore(store.root)
        with store.lock_model(session.id):
            with pytest.raises(ModelLockedError, match=session.id):
                other.lock_model(session.id).__enter__()
            outcome: list[str] = []

            def contend() -> None:
                try:
                    with other.lock_model(session.id):
                        outcome.append("acquired")
                except ModelLockedError:
                    outcome.append("locked")

            thread = threading.Thread(target=contend)
            thread.start()
            thread.join(timeout=10)
            assert outcome == ["locked"]
        with other.lock_model(session.id):
            pass

    def test_lock_is_released_on_exception(self, store: SessionStore) -> None:
        session = store.create()
        with pytest.raises(RuntimeError), store.lock_model(session.id):
            raise RuntimeError("boom")
        with store.lock_model(session.id) as lock:
            assert lock.held

    def test_locks_are_per_session(self, store: SessionStore) -> None:
        a, b = store.create(), store.create()
        with store.lock_model(a.id), store.lock_model(b.id):
            pass

    def test_lock_file_is_never_deleted_by_staging_or_pruning(self, store: SessionStore) -> None:
        session = store.create()
        publish_version(store, session.id, b"x")
        with store.lock_model(session.id) as lock:
            store.discard_staging(lock)
            store.prune_model_versions(lock)
        assert (store.root / session.id / LOCK_FILE).is_file()


class TestRecovery:
    def _abandon_staging(self, store: SessionStore, session_id: str) -> Path:
        directory = store.root / session_id / MODELS_DIR / f"{STAGING_PREFIX}deadbeef"
        directory.mkdir(parents=True)
        (directory / MODEL_FILE).write_bytes(b"half an upload")
        return directory

    def test_sweep_removes_abandoned_staging_and_keeps_the_active_version(
        self, store: SessionStore
    ) -> None:
        session = store.create()
        version = publish_version(store, session.id, b"good")
        abandoned = self._abandon_staging(store, session.id)
        restarted = SessionStore(store.root)
        assert restarted.sweep_staging(session.id) == 1
        assert not abandoned.exists()
        assert restarted.active_model(session.id).sha256 == version.sha256
        assert restarted.read_model_bytes(session.id) == b"good"
        assert restarted.list_model_versions(session.id) == [version.sha256]

    def test_sweep_skips_a_busy_session(self, store: SessionStore) -> None:
        session = store.create()
        abandoned = self._abandon_staging(store, session.id)
        with store.lock_model(session.id):
            assert SessionStore(store.root).sweep_staging(session.id) is None
            assert abandoned.exists()
        assert store.sweep_staging(session.id) == 1

    def test_sweep_all_covers_every_session_and_tolerates_an_empty_root(
        self, store: SessionStore
    ) -> None:
        assert store.sweep_all_staging() == 0
        a, b, c = store.create(), store.create(), store.create()
        self._abandon_staging(store, a.id)
        self._abandon_staging(store, b.id)
        with store.lock_model(c.id):
            self._abandon_staging(store, c.id)
            assert SessionStore(store.root).sweep_all_staging() == 2
        assert store.staging_directories(a.id) == []
        assert store.staging_directories(b.id) == []
        assert len(store.staging_directories(c.id)) == 1

    def test_orphan_committed_version_is_harmless_and_prunable(self, store: SessionStore) -> None:
        """A crash between commit() and set_model() leaves a complete but inactive version."""
        session = store.create()
        active = publish_version(store, session.id, b"active")
        with store.lock_model(session.id) as lock, store.stage_model(lock, max_bytes=10) as s:
            s.write(b"orphan")
            s.seal()
            s.write_json(MODEL_SUMMARY_FILE, fake_summary(s.sha256))
            s.write_json(MODEL_INDEX_FILE, fake_index(s.sha256))
            orphan = s.commit()
            # no set_model: simulate the process dying here
        assert store.active_model(session.id).sha256 == active.sha256
        assert sorted(store.list_model_versions(session.id)) == sorted(
            [active.sha256, orphan.sha256]
        )
        with store.lock_model(session.id) as lock:
            assert store.prune_model_versions(lock) == [orphan.sha256]


class TestAtomicWrites:
    def test_session_record_write_retries_windows_sharing_violations(
        self, store: SessionStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        attempts: list[int] = []
        real_replace = os.replace

        def flaky_replace(src: Path, dst: Path) -> None:
            attempts.append(1)
            if len(attempts) < 3:
                raise PermissionError("sharing violation")
            real_replace(src, dst)

        monkeypatch.setattr(os, "replace", flaky_replace)
        monkeypatch.setattr(store_module, "_REPLACE_BACKOFF_SECONDS", 0.0)
        session = store.create()
        assert len(attempts) == 3
        assert store.get(session.id) == session
        assert _names(store.root / session.id) == [SESSION_FILE]

    def test_persistent_replace_failure_is_a_storage_error_without_leftovers(
        self, store: SessionStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session = store.create()
        first = publish_version(store, session.id, b"first")

        def always_fail(src: Path, dst: Path) -> None:
            raise PermissionError("sharing violation")

        monkeypatch.setattr(os, "replace", always_fail)
        monkeypatch.setattr(store_module, "_REPLACE_BACKOFF_SECONDS", 0.0)
        with pytest.raises(StorageError, match="publish the staged"):
            publish_version(store, session.id, b"second")
        assert store.get(session.id).model_hash == first.sha256
        assert store.list_model_versions(session.id) == [first.sha256]
        assert store.staging_directories(session.id) == []
        assert _names(store.root / session.id) == [LOCK_FILE, MODELS_DIR, SESSION_FILE]
        assert not list((store.root / session.id).glob("*.part"))
