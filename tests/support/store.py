"""Store-level helpers: publish a model version without parsing an IFC.

The store validates the *shape* of a version (all artefacts present, summary hash equal to the
bytes' hash); it does not parse IFC. These helpers build the smallest valid version so the
store tests exercise publication, locking and recovery without IfcOpenShell.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from bim_intelligence.store import (
    MODEL_INDEX_FILE,
    MODEL_SUMMARY_FILE,
    ModelVersion,
    SessionStore,
)


def fake_summary(sha256: str, *, project_name: str = "Fake") -> dict[str, Any]:
    return {
        "ifc_schema": "IFC4",
        "model_hash": sha256,
        "project_name": project_name,
        "counts": {},
        "storeys": [],
    }


def fake_index(sha256: str, **summary_overrides: Any) -> dict[str, Any]:
    return {
        "summary": fake_summary(sha256, **summary_overrides),
        "elements": [],
        "duplicate_global_ids": {},
        "malformed_global_ids": {},
    }


def publish_version(
    store: SessionStore, session_id: str, data: bytes, *, project_name: str = "Fake"
) -> ModelVersion:
    """Stage ``data`` with minimal derived artefacts, commit it and make it active."""
    with (
        store.lock_model(session_id) as lock,
        store.stage_model(lock, max_bytes=max(len(data), 1)) as staged,
    ):
        staged.write(data)
        staged.seal()
        sha256 = staged.sha256
        staged.write_json(MODEL_SUMMARY_FILE, fake_summary(sha256, project_name=project_name))
        staged.write_json(MODEL_INDEX_FILE, fake_index(sha256, project_name=project_name))
        version = staged.commit()
        store.set_model(lock, sha256)
    return version


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_digest(directory: Path) -> dict[str, str]:
    """Relative path → SHA-256 of every file under ``directory``; a snapshot for 'unchanged'."""
    return {
        path.relative_to(directory).as_posix(): sha256_of(path.read_bytes())
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }
