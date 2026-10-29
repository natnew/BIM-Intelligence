"""Model ingestion: lock → stage → hash → parse → index → commit → activate (ADR-017).

Everything an upload produces — the bytes, the ``ModelIndex`` and the ``ModelSummary`` — is
built inside one staging directory, validated, published as a single immutable version
directory and only then made active by one atomic write of the session record. A failure at
any step before the final write leaves the previously active version exactly as it was, and
no reader can observe an index that was not built from the bytes it is served with
(FR-ING-01..03, C-04).
"""

from __future__ import annotations

from collections.abc import Iterable

from bim_intelligence.bim.errors import IfcLoadError
from bim_intelligence.bim.indexer import build_index
from bim_intelligence.bim.loader import open_ifc
from bim_intelligence.bim.model_index import ModelIndex
from bim_intelligence.schemas import ModelSummary
from bim_intelligence.store import (
    MODEL_INDEX_FILE,
    MODEL_SUMMARY_FILE,
    ModelVersion,
    SessionStore,
    StorageError,
)


def ingest_model(
    store: SessionStore, session_id: str, chunks: Iterable[bytes], *, max_bytes: int
) -> ModelIndex:
    """Store, index and activate an uploaded IFC for ``session_id``; returns the new index.

    Raises :class:`~bim_intelligence.store.ModelLockedError` without waiting if another upload
    (or, once runs exist, a review) holds the session's model lock.
    """
    with store.lock_model(session_id) as lock:
        store.discard_staging(lock)
        with store.stage_model(lock, max_bytes=max_bytes) as staged:
            for chunk in chunks:
                staged.write(chunk)
            if staged.size == 0:
                raise IfcLoadError("The uploaded file is empty.")
            model = open_ifc(staged.seal())
            index = build_index(model, model_hash=staged.sha256)
            del model  # release IfcOpenShell's handle before the directory rename (Windows)
            if index.summary.model_hash != staged.sha256:
                raise StorageError("The built index does not describe the uploaded bytes.")
            staged.write_json(MODEL_INDEX_FILE, index.model_dump(mode="json"))
            staged.write_json(MODEL_SUMMARY_FILE, index.summary.model_dump(mode="json"))
            version = staged.commit()
        store.set_model(lock, version.sha256)
    return index


def load_index(version: ModelVersion) -> ModelIndex:
    return ModelIndex.model_validate(version.read_json(MODEL_INDEX_FILE))


def load_summary(version: ModelVersion) -> ModelSummary:
    return ModelSummary.model_validate(version.read_json(MODEL_SUMMARY_FILE))
