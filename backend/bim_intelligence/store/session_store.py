"""File-system session store (ADR-006).

Layout::

    {root}/{session_id}/
        session.json          Session record
        model.ifc             uploaded IFC, byte-for-byte (C-04: never rewritten)
        model_index.json      ModelIndex snapshot
        model_summary.json    ModelSummary

Three properties make this safe to expose through an HTTP API:

* a session id must match ``SESSION_ID_PATTERN`` before it is joined to a path;
* only the fixed artefact names above can be addressed — client filenames never reach disk;
* every write goes to a temporary file in the same directory and is published with
  ``os.replace``, so readers see either the previous or the new content, never a partial file.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import IO, Any

from pydantic import ValidationError

from bim_intelligence.schemas import SESSION_ID_PATTERN, Session
from bim_intelligence.schemas.canonical import canonical_json
from bim_intelligence.store.errors import (
    ArtefactNotFoundError,
    InvalidSessionIdError,
    SessionNotFoundError,
    StorageError,
    UploadTooLargeError,
)

SESSION_FILE = "session.json"
MODEL_FILE = "model.ifc"
MODEL_INDEX_FILE = "model_index.json"
MODEL_SUMMARY_FILE = "model_summary.json"

ARTEFACTS: frozenset[str] = frozenset(
    {SESSION_FILE, MODEL_FILE, MODEL_INDEX_FILE, MODEL_SUMMARY_FILE}
)

_SESSION_ID_RE = re.compile(SESSION_ID_PATTERN)
_TEMP_SUFFIX = ".part"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class StoredModel:
    """Outcome of a committed model upload."""

    sha256: str
    size: int


class StagedUpload:
    """A model upload in progress: hashed and size-capped while written, published on commit.

    Used as a context manager: ``write()`` chunks, ``seal()`` to make the bytes readable for
    validation, then ``commit()``. Leaving the block without ``commit()`` — including via an
    exception raised by validation or indexing — deletes the temporary file and leaves any
    previously stored model untouched.
    """

    def __init__(self, target: Path, max_bytes: int) -> None:
        self._target = target
        self._max_bytes = max_bytes
        self._temp = target.with_name(f"{target.name}.{uuid.uuid4().hex}{_TEMP_SUFFIX}")
        self._handle: IO[bytes] | None = None
        self._hasher = hashlib.sha256()
        self._size = 0
        self._sealed = False
        self._committed = False

    @property
    def path(self) -> Path:
        """Location of the bytes written so far; valid until the context exits."""
        return self._target if self._committed else self._temp

    @property
    def size(self) -> int:
        return self._size

    @property
    def sha256(self) -> str:
        return self._hasher.hexdigest()

    @property
    def committed(self) -> bool:
        return self._committed

    def __enter__(self) -> StagedUpload:
        try:
            self._handle = open(self._temp, "xb")
        except OSError as exc:
            raise StorageError("Could not create a temporary file for the upload.") from exc
        return self

    def write(self, chunk: bytes) -> None:
        if self._handle is None or self._committed:
            raise StorageError("Staged upload is not open for writing.")
        if self._size + len(chunk) > self._max_bytes:
            raise UploadTooLargeError(self._max_bytes)
        self._handle.write(chunk)
        self._hasher.update(chunk)
        self._size += len(chunk)

    def seal(self) -> Path:
        """Finish writing. The staged bytes are readable at ``path`` until the context exits."""
        if self._committed:
            raise StorageError("Staged upload is already committed.")
        self._close_handle()
        self._sealed = True
        return self._temp

    def commit(self) -> StoredModel:
        """Flush, fsync and atomically replace the target with the staged bytes."""
        if self._committed or not (self._sealed or self._handle is not None):
            raise StorageError("Staged upload cannot be committed twice.")
        self._close_handle()
        try:
            os.replace(self._temp, self._target)
        except OSError as exc:
            raise StorageError("Could not publish the uploaded model.") from exc
        self._committed = True
        return StoredModel(sha256=self.sha256, size=self._size)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._close_handle()
        if not self._committed:
            self._temp.unlink(missing_ok=True)

    def _close_handle(self) -> None:
        if self._handle is None:
            return
        try:
            self._handle.flush()
            os.fsync(self._handle.fileno())
        finally:
            self._handle.close()
            self._handle = None


class SessionStore:
    """Sessions as directories under ``root``; one instance per request is cheap."""

    def __init__(
        self,
        root: Path,
        *,
        clock: Callable[[], datetime] = _utc_now,
        id_factory: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self.root = root
        self._clock = clock
        self._id_factory = id_factory

    # -- sessions -----------------------------------------------------------------------

    def create(self) -> Session:
        session = Session(id=self._id_factory(), created_at=self._clock(), status="created")
        directory = self.root / session.id
        try:
            directory.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            raise StorageError("Could not create the session directory.") from exc
        self._write_session(session)
        return session

    def get(self, session_id: str) -> Session:
        path = self.path_for(session_id, SESSION_FILE)
        if not path.is_file():
            raise SessionNotFoundError(session_id)
        try:
            return Session.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError, ValueError) as exc:
            raise StorageError(f"Session {session_id} has an unreadable record.") from exc

    def exists(self, session_id: str) -> bool:
        try:
            self.get(session_id)
        except SessionNotFoundError:
            return False
        return True

    # -- paths --------------------------------------------------------------------------

    def path_for(self, session_id: str, artefact: str) -> Path:
        """Absolute path of a fixed-name artefact. Validates both components first."""
        if not _SESSION_ID_RE.fullmatch(session_id):
            raise InvalidSessionIdError(session_id)
        if artefact not in ARTEFACTS:
            raise ValueError(f"Unknown artefact {artefact!r}; expected one of {sorted(ARTEFACTS)}")
        path = self.root / session_id / artefact
        # Defence in depth: the two checks above already make escape impossible.
        if not path.resolve().is_relative_to(self.root.resolve()):  # pragma: no cover
            raise InvalidSessionIdError(session_id)
        return path

    # -- JSON artefacts -----------------------------------------------------------------

    def write_json(self, session_id: str, artefact: str, value: Any) -> Path:
        """Canonical JSON, written atomically. ``value`` must already be JSON-compatible."""
        path = self.path_for(session_id, artefact)
        self._require_session(session_id)
        try:
            text = canonical_json(value)
        except (TypeError, ValueError) as exc:
            raise StorageError(f"{artefact!r} is not JSON-serialisable: {exc}") from exc
        self._atomic_write_text(path, text)
        return path

    def read_json(self, session_id: str, artefact: str) -> Any:
        path = self.path_for(session_id, artefact)
        self._require_session(session_id)
        if not path.is_file():
            raise ArtefactNotFoundError(session_id, artefact)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise StorageError(f"Session {session_id}: {artefact!r} is unreadable.") from exc

    # -- model bytes --------------------------------------------------------------------

    def stage_model(self, session_id: str, *, max_bytes: int) -> StagedUpload:
        """Begin a size-capped, hashed upload of ``model.ifc``; see :class:`StagedUpload`."""
        target = self.path_for(session_id, MODEL_FILE)
        self._require_session(session_id)
        return StagedUpload(target, max_bytes)

    def store_model(
        self, session_id: str, chunks: Iterable[bytes], *, max_bytes: int
    ) -> StoredModel:
        """Write and record a model in one step (no validation between write and commit)."""
        with self.stage_model(session_id, max_bytes=max_bytes) as staged:
            for chunk in chunks:
                staged.write(chunk)
            stored = staged.commit()
        self.set_model(session_id, stored.sha256)
        return stored

    def set_model(self, session_id: str, model_hash: str) -> Session:
        """Record that ``model.ifc`` with this hash is the session's current model."""
        current = self.get(session_id)
        updated = current.model_copy(update={"status": "model_ready", "model_hash": model_hash})
        self._write_session(Session.model_validate(updated.model_dump()))
        return updated

    def has_model(self, session_id: str) -> bool:
        return self.path_for(session_id, MODEL_FILE).is_file()

    def read_model_bytes(self, session_id: str) -> bytes:
        path = self.path_for(session_id, MODEL_FILE)
        self._require_session(session_id)
        if not path.is_file():
            raise ArtefactNotFoundError(session_id, MODEL_FILE)
        try:
            return path.read_bytes()
        except OSError as exc:
            raise StorageError(f"Session {session_id}: model is unreadable.") from exc

    # -- internals ----------------------------------------------------------------------

    def _require_session(self, session_id: str) -> None:
        if not (self.root / session_id / SESSION_FILE).is_file():
            raise SessionNotFoundError(session_id)

    def _write_session(self, session: Session) -> None:
        path = self.root / session.id / SESSION_FILE
        self._atomic_write_text(path, canonical_json(session.model_dump(mode="json")))

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        temp = path.with_name(f"{path.name}.{uuid.uuid4().hex}{_TEMP_SUFFIX}")
        try:
            with open(temp, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        except OSError as exc:
            temp.unlink(missing_ok=True)
            raise StorageError(f"Could not write {path.name!r}.") from exc
