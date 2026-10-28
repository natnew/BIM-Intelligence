"""Model ingestion: stage → hash → parse → index → publish (FR-ING-01..03, C-04).

The uploaded bytes are written to a staged file, parsed and indexed from there, and only
published as ``model.ifc`` once indexing has succeeded. A malformed re-upload therefore never
replaces a good model, and the stored file is byte-identical to what the client sent.
"""

from __future__ import annotations

from collections.abc import Iterable

from bim_intelligence.bim.errors import IfcLoadError
from bim_intelligence.bim.indexer import build_index
from bim_intelligence.bim.loader import open_ifc
from bim_intelligence.bim.model_index import ModelIndex
from bim_intelligence.schemas import ModelSummary
from bim_intelligence.store import MODEL_INDEX_FILE, MODEL_SUMMARY_FILE, SessionStore


def ingest_model(
    store: SessionStore, session_id: str, chunks: Iterable[bytes], *, max_bytes: int
) -> ModelIndex:
    """Store and index an uploaded IFC for ``session_id``; returns the new index."""
    with store.stage_model(session_id, max_bytes=max_bytes) as staged:
        for chunk in chunks:
            staged.write(chunk)
        if staged.size == 0:
            raise IfcLoadError("The uploaded file is empty.")
        model = open_ifc(staged.seal())
        index = build_index(model, model_hash=staged.sha256)
        del model  # release IfcOpenShell's handle before the rename (Windows)
        staged.commit()
    store.write_json(session_id, MODEL_INDEX_FILE, index.model_dump(mode="json"))
    store.write_json(session_id, MODEL_SUMMARY_FILE, index.summary.model_dump(mode="json"))
    store.set_model(session_id, index.summary.model_hash)
    return index


def load_index(store: SessionStore, session_id: str) -> ModelIndex:
    return ModelIndex.model_validate(store.read_json(session_id, MODEL_INDEX_FILE))


def load_summary(store: SessionStore, session_id: str) -> ModelSummary:
    return ModelSummary.model_validate(store.read_json(session_id, MODEL_SUMMARY_FILE))
