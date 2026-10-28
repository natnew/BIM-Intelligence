"""SessionStore: UUID-scoped directories, fixed filenames, atomic writes (ADR-006, FR-ING-03).

AC-02: the stored IFC's SHA-256 equals the uploaded bytes. The tests also pin the path-safety
properties ARCHITECTURE §13 relies on: no client-controlled path component ever reaches the
file system.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from bim_intelligence.schemas import SESSION_ID_PATTERN
from bim_intelligence.store import (
    MODEL_FILE,
    MODEL_INDEX_FILE,
    MODEL_SUMMARY_FILE,
    SESSION_FILE,
    ArtefactNotFoundError,
    InvalidSessionIdError,
    SessionNotFoundError,
    SessionStore,
    StorageError,
    UploadTooLargeError,
)
from fixtures.make_minimal_ifc import IFC_PATH

FIXED_NOW = datetime(2026, 10, 28, 9, 0, tzinfo=timezone.utc)
UNKNOWN_ID = "0f1b7a2e-5c3d-4e8f-9a1b-2c3d4e5f6a7b"


@pytest.fixture
def store(tmp_path: Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions", clock=lambda: FIXED_NOW)


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
        store.store_model(a.id, [b"ISO-10303-21;"], max_bytes=1024)
        assert store.has_model(a.id) is True
        assert store.has_model(b.id) is False
        assert store.get(b.id).model_hash is None

    def test_unknown_session_raises(self, store: SessionStore) -> None:
        with pytest.raises(SessionNotFoundError, match=UNKNOWN_ID):
            store.get(UNKNOWN_ID)
        with pytest.raises(SessionNotFoundError):
            store.read_json(UNKNOWN_ID, MODEL_SUMMARY_FILE)

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
            store.path_for(bad_id, SESSION_FILE)
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
    def test_only_fixed_artefact_names_are_addressable(self, store: SessionStore) -> None:
        session = store.create()
        for name in (SESSION_FILE, MODEL_FILE, MODEL_INDEX_FILE, MODEL_SUMMARY_FILE):
            path = store.path_for(session.id, name)
            assert path.parent == store.root / session.id
            assert path.name == name
        for name in ("../model.ifc", "model.ifc/..", "other.ifc", "", "C:/windows/x"):
            with pytest.raises(ValueError):
                store.path_for(session.id, name)

    def test_paths_stay_inside_the_store_root(self, store: SessionStore) -> None:
        session = store.create()
        path = store.path_for(session.id, MODEL_FILE).resolve()
        assert path.is_relative_to(store.root.resolve())


class TestJson:
    def test_write_is_canonical_and_round_trips(self, store: SessionStore) -> None:
        session = store.create()
        store.write_json(session.id, MODEL_SUMMARY_FILE, {"b": 1, "a": [1, 2]})
        text = store.path_for(session.id, MODEL_SUMMARY_FILE).read_text(encoding="utf-8")
        assert text == '{\n  "a": [\n    1,\n    2\n  ],\n  "b": 1\n}\n'
        assert store.read_json(session.id, MODEL_SUMMARY_FILE) == {"b": 1, "a": [1, 2]}

    def test_write_leaves_no_temporary_files(self, store: SessionStore) -> None:
        session = store.create()
        store.write_json(session.id, MODEL_SUMMARY_FILE, {"a": 1})
        store.write_json(session.id, MODEL_SUMMARY_FILE, {"a": 2})
        names = sorted(p.name for p in (store.root / session.id).iterdir())
        assert names == [MODEL_SUMMARY_FILE, SESSION_FILE]
        assert store.read_json(session.id, MODEL_SUMMARY_FILE) == {"a": 2}

    def test_missing_artefact_raises(self, store: SessionStore) -> None:
        session = store.create()
        with pytest.raises(ArtefactNotFoundError, match=MODEL_SUMMARY_FILE):
            store.read_json(session.id, MODEL_SUMMARY_FILE)

    def test_unserialisable_value_is_a_storage_error_and_writes_nothing(
        self, store: SessionStore
    ) -> None:
        session = store.create()
        with pytest.raises(StorageError):
            store.write_json(session.id, MODEL_SUMMARY_FILE, {"when": FIXED_NOW})
        assert not store.path_for(session.id, MODEL_SUMMARY_FILE).exists()
        assert sorted(p.name for p in (store.root / session.id).iterdir()) == [SESSION_FILE]


class TestModelStorage:
    def test_store_model_writes_fixed_filename_and_sha256(self, store: SessionStore) -> None:
        session = store.create()
        data = IFC_PATH.read_bytes()
        stored = store.store_model(session.id, _chunks(data, 1000), max_bytes=len(data))
        assert stored.sha256 == hashlib.sha256(data).hexdigest()
        assert stored.size == len(data)
        assert store.path_for(session.id, MODEL_FILE).read_bytes() == data
        assert store.read_model_bytes(session.id) == data
        assert store.get(session.id).status == "model_ready"
        assert store.get(session.id).model_hash == stored.sha256

    def test_hash_is_stable_across_sessions(self, store: SessionStore) -> None:
        data = IFC_PATH.read_bytes()
        a = store.store_model(store.create().id, [data], max_bytes=len(data))
        b = store.store_model(store.create().id, _chunks(data, 7), max_bytes=len(data))
        assert a.sha256 == b.sha256

    def test_oversized_upload_is_rejected_and_leaves_nothing_behind(
        self, store: SessionStore
    ) -> None:
        session = store.create()
        with pytest.raises(UploadTooLargeError):
            store.store_model(session.id, _chunks(b"x" * 100, 10), max_bytes=50)
        assert sorted(p.name for p in (store.root / session.id).iterdir()) == [SESSION_FILE]
        assert store.has_model(session.id) is False

    def test_staged_upload_is_discarded_unless_committed(self, store: SessionStore) -> None:
        session = store.create()
        with store.stage_model(session.id, max_bytes=100) as staged:
            staged.write(b"partial")
            assert staged.size == 7
        assert sorted(p.name for p in (store.root / session.id).iterdir()) == [SESSION_FILE]

    def test_failed_staging_keeps_the_previous_model(self, store: SessionStore) -> None:
        session = store.create()
        original = store.store_model(session.id, [b"first"], max_bytes=100)
        with pytest.raises(RuntimeError), store.stage_model(session.id, max_bytes=100) as staged:
            staged.write(b"second")
            raise RuntimeError("validation failed downstream")
        assert store.read_model_bytes(session.id) == b"first"
        assert store.get(session.id).model_hash == original.sha256

    def test_committed_staging_replaces_the_model_atomically(self, store: SessionStore) -> None:
        session = store.create()
        store.store_model(session.id, [b"first"], max_bytes=100)
        with store.stage_model(session.id, max_bytes=100) as staged:
            staged.write(b"second")
            staged.commit()
        assert store.read_model_bytes(session.id) == b"second"
        names = sorted(p.name for p in (store.root / session.id).iterdir())
        assert names == [MODEL_FILE, SESSION_FILE]

    def test_write_after_commit_is_an_error(self, store: SessionStore) -> None:
        session = store.create()
        with store.stage_model(session.id, max_bytes=100) as staged:
            staged.write(b"x")
            staged.commit()
            with pytest.raises(StorageError):
                staged.write(b"y")
            with pytest.raises(StorageError):
                staged.commit()

    def test_sealed_bytes_are_readable_before_commit(self, store: SessionStore) -> None:
        session = store.create()
        with store.stage_model(session.id, max_bytes=100) as staged:
            staged.write(b"abc")
            path = staged.seal()
            assert path.read_bytes() == b"abc"
            assert path.parent == store.root / session.id
            with pytest.raises(StorageError):
                staged.write(b"d")
            staged.commit()
        assert store.read_model_bytes(session.id) == b"abc"

    def test_model_bytes_absent_until_uploaded(self, store: SessionStore) -> None:
        session = store.create()
        with pytest.raises(ArtefactNotFoundError):
            store.read_model_bytes(session.id)

    def test_set_model_records_hash_in_session_json(self, store: SessionStore) -> None:
        session = store.create()
        store.set_model(session.id, "a" * 64)
        record = json.loads(store.path_for(session.id, SESSION_FILE).read_text(encoding="utf-8"))
        assert record["model_hash"] == "a" * 64
        assert record["status"] == "model_ready"
        assert "path" not in record


def _chunks(data: bytes, size: int) -> list[bytes]:
    return [data[i : i + size] for i in range(0, len(data), size)]
