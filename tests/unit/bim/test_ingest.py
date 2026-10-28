"""``ingest_model``: upload → hash → parse → index → atomic publish (FR-ING-01..03, AC-02)."""

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
    MODEL_FILE,
    MODEL_INDEX_FILE,
    MODEL_SUMMARY_FILE,
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


def test_ingest_persists_bytes_index_and_summary(store: SessionStore) -> None:
    session = store.create()
    index = ingest_model(store, session.id, [FIXTURE_BYTES], max_bytes=len(FIXTURE_BYTES))
    assert isinstance(index, ModelIndex)
    assert index.summary.model_hash == FIXTURE_HASH
    assert index.summary.counts["IfcWall"] == 3

    names = sorted(p.name for p in (store.root / session.id).iterdir())
    assert names == [MODEL_FILE, MODEL_INDEX_FILE, MODEL_SUMMARY_FILE, SESSION_FILE]
    assert store.read_model_bytes(session.id) == FIXTURE_BYTES, "stored bytes must be untouched"
    assert store.get(session.id).status == "model_ready"
    assert store.get(session.id).model_hash == FIXTURE_HASH

    assert load_summary(store, session.id) == index.summary
    assert load_index(store, session.id) == index


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
    assert load_summary(store, session.id).model_hash == FIXTURE_HASH
    names = sorted(p.name for p in (store.root / session.id).iterdir())
    assert names == [MODEL_FILE, MODEL_INDEX_FILE, MODEL_SUMMARY_FILE, SESSION_FILE]


def test_empty_upload_is_a_load_error(store: SessionStore) -> None:
    session = store.create()
    with pytest.raises(IfcLoadError, match="empty"):
        ingest_model(store, session.id, [], max_bytes=10**6)
    assert sorted(p.name for p in (store.root / session.id).iterdir()) == [SESSION_FILE]


def test_oversized_upload_never_reaches_the_parser(store: SessionStore) -> None:
    session = store.create()
    with pytest.raises(UploadTooLargeError):
        ingest_model(store, session.id, [FIXTURE_BYTES], max_bytes=len(FIXTURE_BYTES) - 1)
    assert sorted(p.name for p in (store.root / session.id).iterdir()) == [SESSION_FILE]


def test_loading_before_upload_raises(store: SessionStore) -> None:
    session = store.create()
    with pytest.raises(ArtefactNotFoundError):
        load_summary(store, session.id)
    with pytest.raises(ArtefactNotFoundError):
        load_index(store, session.id)


def test_reupload_replaces_the_model(store: SessionStore) -> None:
    session = store.create()
    ingest_model(store, session.id, [FIXTURE_BYTES], max_bytes=10**6)
    # Same bytes with a trailing newline: a different hash, still a valid IFC.
    variant = FIXTURE_BYTES + b"\n"
    index = ingest_model(store, session.id, [variant], max_bytes=10**6)
    assert index.summary.model_hash == hashlib.sha256(variant).hexdigest()
    assert store.read_model_bytes(session.id) == variant
    assert load_summary(store, session.id).model_hash == index.summary.model_hash
