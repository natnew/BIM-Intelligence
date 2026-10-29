"""``ingest_model``: lock → stage → hash → parse → index → commit → activate (FR-ING-01..03)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from bim_intelligence.bim import (
    IfcLoadError,
    ModelIndex,
    ingest_model,
    load_index,
    load_summary,
)
from bim_intelligence.store import (
    LOCK_FILE,
    MODEL_FILE,
    MODEL_INDEX_FILE,
    MODEL_SUMMARY_FILE,
    MODELS_DIR,
    SESSION_FILE,
    ArtefactNotFoundError,
    SessionStore,
    UploadTooLargeError,
)
from fixtures.make_minimal_ifc import IFC_PATH

FIXTURE_BYTES = IFC_PATH.read_bytes()
FIXTURE_HASH = hashlib.sha256(FIXTURE_BYTES).hexdigest()


@pytest.fixture
def store(tmp_path: Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions")


def _names(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir())


def test_ingest_publishes_bytes_index_and_summary_as_one_version(store: SessionStore) -> None:
    session = store.create()
    index = ingest_model(store, session.id, [FIXTURE_BYTES], max_bytes=len(FIXTURE_BYTES))
    assert isinstance(index, ModelIndex)
    assert index.summary.model_hash == FIXTURE_HASH
    assert index.summary.counts["IfcWall"] == 3

    session_dir = store.root / session.id
    assert _names(session_dir) == [LOCK_FILE, MODELS_DIR, SESSION_FILE]
    assert _names(session_dir / MODELS_DIR) == [FIXTURE_HASH]
    assert _names(session_dir / MODELS_DIR / FIXTURE_HASH) == [
        MODEL_FILE,
        MODEL_INDEX_FILE,
        MODEL_SUMMARY_FILE,
    ]
    assert store.read_model_bytes(session.id) == FIXTURE_BYTES, "stored bytes must be untouched"
    assert store.get(session.id).status == "model_ready"
    assert store.get(session.id).model_hash == FIXTURE_HASH

    version = store.active_model(session.id)
    assert version.sha256 == FIXTURE_HASH
    assert load_summary(version) == index.summary
    assert load_index(version) == index


def test_ingest_is_deterministic_across_sessions(store: SessionStore) -> None:
    a = ingest_model(store, store.create().id, [FIXTURE_BYTES], max_bytes=10**6)
    b = ingest_model(store, store.create().id, [FIXTURE_BYTES], max_bytes=10**6)
    assert a == b


def test_malformed_upload_raises_and_keeps_the_previous_model(store: SessionStore) -> None:
    session = store.create()
    ingest_model(store, session.id, [FIXTURE_BYTES], max_bytes=10**6)
    with pytest.raises(IfcLoadError):
        ingest_model(store, session.id, [b"definitely not an IFC"], max_bytes=10**6)
    assert store.read_model_bytes(session.id) == FIXTURE_BYTES
    assert store.get(session.id).model_hash == FIXTURE_HASH
    assert load_summary(store.active_model(session.id)).model_hash == FIXTURE_HASH
    assert store.list_model_versions(session.id) == [FIXTURE_HASH]
    assert store.staging_directories(session.id) == []


def test_empty_upload_is_a_load_error(store: SessionStore) -> None:
    session = store.create()
    with pytest.raises(IfcLoadError, match="empty"):
        ingest_model(store, session.id, [], max_bytes=10**6)
    assert store.has_model(session.id) is False
    assert store.list_model_versions(session.id) == []
    assert store.staging_directories(session.id) == []


def test_oversized_upload_never_reaches_the_parser(store: SessionStore) -> None:
    session = store.create()
    with pytest.raises(UploadTooLargeError):
        ingest_model(store, session.id, [FIXTURE_BYTES], max_bytes=len(FIXTURE_BYTES) - 1)
    assert store.has_model(session.id) is False
    assert store.staging_directories(session.id) == []


def test_loading_before_upload_raises(store: SessionStore) -> None:
    session = store.create()
    with pytest.raises(ArtefactNotFoundError):
        store.active_model(session.id)


def test_reupload_replaces_the_active_version_and_retains_the_old_one(
    store: SessionStore,
) -> None:
    session = store.create()
    ingest_model(store, session.id, [FIXTURE_BYTES], max_bytes=10**6)
    # Same bytes with a trailing newline: a different hash, still a valid IFC.
    variant = FIXTURE_BYTES + b"\n"
    variant_hash = hashlib.sha256(variant).hexdigest()
    index = ingest_model(store, session.id, [variant], max_bytes=10**6)
    assert index.summary.model_hash == variant_hash
    assert store.read_model_bytes(session.id) == variant
    assert load_summary(store.active_model(session.id)).model_hash == variant_hash
    assert sorted(store.list_model_versions(session.id)) == sorted([FIXTURE_HASH, variant_hash])
    pinned = store.model_version(session.id, FIXTURE_HASH)
    assert pinned.read_bytes() == FIXTURE_BYTES, "a pinned snapshot survives replacement"
    assert load_index(pinned).summary.model_hash == FIXTURE_HASH


def test_identical_reupload_is_idempotent(store: SessionStore) -> None:
    session = store.create()
    first = ingest_model(store, session.id, [FIXTURE_BYTES], max_bytes=10**6)
    second = ingest_model(store, session.id, [FIXTURE_BYTES], max_bytes=10**6)
    assert first == second
    assert store.list_model_versions(session.id) == [FIXTURE_HASH]
    assert store.staging_directories(session.id) == []
