"""File-system session store (ADR-006, ADR-017).

Layout::

    {root}/{session_id}/
        session.json              Session record; ``model_hash`` names the active model version
        model.lock                advisory lock that serialises model publication
        models/
            {sha256}/             one immutable, content-addressed model version
                model.ifc         uploaded IFC, byte-for-byte (C-04: never rewritten)
                model_index.json  ModelIndex built from exactly those bytes
                model_summary.json
            .staging-{hex}/       a version under construction; nothing else ever reads it

Publication is a two-step transaction under the session's model lock:

1. ``StagedModel.commit()`` validates the staged artefacts and moves the whole staging directory
   to ``models/{sha256}/`` with one rename. A version directory therefore either exists complete
   or not at all, and it is never modified afterwards.
2. ``SessionStore.set_model()`` points ``session.json`` at that version with one atomic replace.

Readers resolve the active version once (:meth:`SessionStore.active_model`) and read bytes,
index and summary from that single directory, so no reader can observe artefacts from two
versions in one request. Superseded versions stay on disk until pruned, which is what makes a
review pinned to a hash safe across a re-upload.

Three further properties make the store safe to expose through an HTTP API: a session id must
match ``SESSION_ID_PATTERN`` before it is joined to a path; only fixed artefact names are
addressable, so client filenames never reach disk; and every write goes to a temporary file in
the same directory and is published with ``os.replace``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import IO, Any, TypeVar

from pydantic import ValidationError

from bim_intelligence.schemas import SESSION_ID_PATTERN, ModelSummary, Session
from bim_intelligence.schemas.canonical import canonical_json
from bim_intelligence.store.errors import (
    ArtefactNotFoundError,
    IncompleteModelVersionError,
    InvalidSessionIdError,
    ModelLockedError,
    SessionNotFoundError,
    StorageError,
    UploadTooLargeError,
)
from bim_intelligence.store.locking import FileLock

logger = logging.getLogger(__name__)

SESSION_FILE = "session.json"
LOCK_FILE = "model.lock"
MODELS_DIR = "models"
MODEL_FILE = "model.ifc"
MODEL_INDEX_FILE = "model_index.json"
MODEL_SUMMARY_FILE = "model_summary.json"

MODEL_ARTEFACTS: frozenset[str] = frozenset({MODEL_FILE, MODEL_INDEX_FILE, MODEL_SUMMARY_FILE})
DERIVED_ARTEFACTS: frozenset[str] = frozenset({MODEL_INDEX_FILE, MODEL_SUMMARY_FILE})
STAGING_PREFIX = ".staging-"

_SESSION_ID_RE = re.compile(SESSION_ID_PATTERN)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TEMP_SUFFIX = ".part"
_REPLACE_ATTEMPTS = 20
_REPLACE_BACKOFF_SECONDS = 0.01

T = TypeVar("T")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _replace(src: Path, dst: Path) -> None:
    """``os.replace`` with a bounded retry for Windows sharing violations.

    On Windows a file that another thread has open for reading cannot be replaced. Reads in
    this store take microseconds, so a short retry turns a spurious failure into a brief wait.
    Kept as a module attribute so tests can inject publication failures.
    """
    _retry_sharing_violation(lambda: os.replace(src, dst))


def _read_text_retry(path: Path) -> str:
    """Read a file that may be mid-replacement on Windows (only ``session.json`` ever is)."""
    return _retry_sharing_violation(lambda: path.read_text(encoding="utf-8"))


def _retry_sharing_violation(operation: Callable[[], T]) -> T:
    for attempt in range(_REPLACE_ATTEMPTS):
        try:
            return operation()
        except PermissionError:
            if attempt == _REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(_REPLACE_BACKOFF_SECONDS * (attempt + 1))
    raise AssertionError("unreachable")  # pragma: no cover


def _fsync_dir(path: Path) -> None:
    """Make renames inside ``path`` durable where the platform allows a directory fsync."""
    if os.name != "posix":
        return
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _write_file(path: Path, data: bytes) -> None:
    with open(path, "xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


@dataclass(frozen=True)
class ModelVersion:
    """One immutable model version: the bytes, index and summary built from them, together."""

    session_id: str
    sha256: str
    directory: Path

    def path_for(self, artefact: str) -> Path:
        if artefact not in MODEL_ARTEFACTS:
            raise ValueError(
                f"Unknown model artefact {artefact!r}; expected one of {sorted(MODEL_ARTEFACTS)}"
            )
        return self.directory / artefact

    def missing_artefacts(self) -> list[str]:
        return sorted(name for name in MODEL_ARTEFACTS if not (self.directory / name).is_file())

    @property
    def is_complete(self) -> bool:
        return not self.missing_artefacts()

    def read_json(self, artefact: str) -> Any:
        path = self.path_for(artefact)
        if not path.is_file():
            raise IncompleteModelVersionError(self.session_id, self.sha256, [artefact])
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise StorageError(
                f"Session {self.session_id}: {artefact!r} of model version "
                f"{self.sha256[:12]} is unreadable."
            ) from exc

    def read_bytes(self) -> bytes:
        path = self.path_for(MODEL_FILE)
        if not path.is_file():
            raise IncompleteModelVersionError(self.session_id, self.sha256, [MODEL_FILE])
        try:
            return path.read_bytes()
        except OSError as exc:
            raise StorageError(
                f"Session {self.session_id}: model version {self.sha256[:12]} is unreadable."
            ) from exc


class ModelLock:
    """Exclusive, non-blocking lock over one session's model publication.

    Holding the lock is a prerequisite for staging, committing, activating and pruning model
    versions; the store takes the lock object itself as proof, so none of those operations can
    be reached without it. Acquisition raises :class:`ModelLockedError` rather than waiting.
    """

    def __init__(self, session_id: str, path: Path) -> None:
        self.session_id = session_id
        self._lock = FileLock(path)

    @property
    def held(self) -> bool:
        return self._lock.held

    def __enter__(self) -> ModelLock:
        try:
            acquired = self._lock.acquire()
        except OSError as exc:
            raise StorageError("Could not open the session's model lock.") from exc
        if not acquired:
            raise ModelLockedError(self.session_id)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._lock.release()


class StagedModel:
    """A model version under construction inside ``models/.staging-{hex}/``.

    ``write()`` the upload (hashed and size-capped as it goes), ``seal()`` it so the bytes can be
    parsed and indexed in place, add the derived artefacts with ``write_json()``, then
    ``commit()`` to validate the set and move the directory to ``models/{sha256}/`` in one
    rename. Leaving the ``with`` block without a commit — including via an exception from
    parsing, indexing or serialisation — removes the staging directory. Nothing outside it
    changes before ``commit()`` returns, so a failed upload leaves no trace.
    """

    def __init__(self, session_id: str, models_dir: Path, max_bytes: int) -> None:
        self._session_id = session_id
        self._models_dir = models_dir
        self._max_bytes = max_bytes
        self._dir = models_dir / f"{STAGING_PREFIX}{uuid.uuid4().hex}"
        self._handle: IO[bytes] | None = None
        self._hasher = hashlib.sha256()
        self._size = 0
        self._sealed = False
        self._committed: ModelVersion | None = None

    @property
    def directory(self) -> Path:
        """The staging directory; valid until the context exits or ``commit()`` returns."""
        return self._dir

    @property
    def model_path(self) -> Path:
        return self._dir / MODEL_FILE

    @property
    def size(self) -> int:
        return self._size

    @property
    def sha256(self) -> str:
        return self._hasher.hexdigest()

    @property
    def committed(self) -> ModelVersion | None:
        return self._committed

    def __enter__(self) -> StagedModel:
        try:
            self._dir.mkdir(parents=True, exist_ok=False)
            self._handle = open(self.model_path, "xb")
        except OSError as exc:
            shutil.rmtree(self._dir, ignore_errors=True)
            raise StorageError("Could not create a staging directory for the upload.") from exc
        return self

    def write(self, chunk: bytes) -> None:
        if self._handle is None or self._sealed:
            raise StorageError("Staged model is not open for writing.")
        if self._size + len(chunk) > self._max_bytes:
            raise UploadTooLargeError(self._max_bytes)
        self._handle.write(chunk)
        self._hasher.update(chunk)
        self._size += len(chunk)

    def seal(self) -> Path:
        """Finish writing; the bytes stay readable at ``model_path`` until the context exits."""
        if self._committed is not None:
            raise StorageError("Staged model is already committed.")
        self._close_handle()
        self._sealed = True
        return self.model_path

    def write_json(self, artefact: str, value: Any) -> Path:
        """Add a derived artefact (canonical JSON) to the staged version."""
        if artefact not in DERIVED_ARTEFACTS:
            raise ValueError(
                f"Unknown derived artefact {artefact!r}; "
                f"expected one of {sorted(DERIVED_ARTEFACTS)}"
            )
        if not self._sealed or self._committed is not None:
            raise StorageError(
                "Derived artefacts can only be staged after seal() and before commit()."
            )
        try:
            text = canonical_json(value)
        except (TypeError, ValueError) as exc:
            raise StorageError(f"{artefact!r} is not JSON-serialisable: {exc}") from exc
        path = self._dir / artefact
        try:
            _write_file(path, text.encode("utf-8"))
        except OSError as exc:
            raise StorageError(f"Could not stage {artefact!r}.") from exc
        return path

    def commit(self) -> ModelVersion:
        """Validate the staged set and publish it as ``models/{sha256}/`` with one rename.

        The version is complete and immutable after this returns but not yet active; call
        :meth:`SessionStore.set_model` to point the session at it. Re-uploading bytes that are
        already present as a version discards the staging directory and returns the existing
        version, since content addressing makes the two indistinguishable.
        """
        if self._committed is not None:
            raise StorageError("Staged model is already committed.")
        if not self._sealed:
            raise StorageError("Staged model must be sealed before commit().")
        self._validate_staged()
        target = self._models_dir / self.sha256
        version = ModelVersion(self._session_id, self.sha256, target)
        if target.is_dir():
            if version.is_complete:
                shutil.rmtree(self._dir, ignore_errors=True)
                self._committed = version
                return version
            # A damaged copy (e.g. a partially failed prune) is replaced by this complete one.
            shutil.rmtree(target, ignore_errors=True)
            if target.exists():
                raise StorageError("A damaged copy of this model version could not be replaced.")
        _fsync_dir(self._dir)
        try:
            _replace(self._dir, target)
        except OSError as exc:
            raise StorageError("Could not publish the staged model version.") from exc
        _fsync_dir(self._models_dir)
        self._committed = version
        return version

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._close_handle()
        if self._committed is None:
            shutil.rmtree(self._dir, ignore_errors=True)

    def _close_handle(self) -> None:
        if self._handle is None:
            return
        try:
            self._handle.flush()
            os.fsync(self._handle.fileno())
        finally:
            self._handle.close()
            self._handle = None

    def _validate_staged(self) -> None:
        """Refuse to publish unless every artefact is present and describes these bytes."""
        if self._size == 0:
            raise StorageError("Staged model is empty.")
        missing = [name for name in MODEL_ARTEFACTS if not (self._dir / name).is_file()]
        if missing:
            raise IncompleteModelVersionError(self._session_id, self.sha256, missing)
        try:
            actual_size = self.model_path.stat().st_size
            summary_text = (self._dir / MODEL_SUMMARY_FILE).read_text(encoding="utf-8")
            index_size = (self._dir / MODEL_INDEX_FILE).stat().st_size
        except OSError as exc:
            raise StorageError("Could not read back the staged model artefacts.") from exc
        if actual_size != self._size:
            raise StorageError(
                f"Staged model is {actual_size} bytes on disk but {self._size} were written."
            )
        if index_size == 0:
            raise StorageError(f"Staged {MODEL_INDEX_FILE!r} is empty.")
        try:
            summary = ModelSummary.model_validate_json(summary_text)
        except ValidationError as exc:
            raise StorageError(
                f"Staged {MODEL_SUMMARY_FILE!r} is not a valid ModelSummary."
            ) from exc
        if summary.model_hash != self.sha256:
            raise StorageError(
                f"Staged summary describes model {summary.model_hash[:12]}, "
                f"not the uploaded bytes {self.sha256[:12]}."
            )


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
        path = self.session_dir(session_id) / SESSION_FILE
        if not path.is_file():
            raise SessionNotFoundError(session_id)
        try:
            return Session.model_validate_json(_read_text_retry(path))
        except (OSError, ValidationError, ValueError) as exc:
            raise StorageError(f"Session {session_id} has an unreadable record.") from exc

    def exists(self, session_id: str) -> bool:
        try:
            self.get(session_id)
        except SessionNotFoundError:
            return False
        return True

    def session_ids(self) -> list[str]:
        """Ids of every directory under ``root`` that holds a session record."""
        if not self.root.is_dir():
            return []
        return sorted(
            child.name
            for child in self.root.iterdir()
            if _SESSION_ID_RE.fullmatch(child.name) and (child / SESSION_FILE).is_file()
        )

    # -- paths --------------------------------------------------------------------------

    def session_dir(self, session_id: str) -> Path:
        """Directory of a session. Validates the id before it is joined to a path."""
        if not _SESSION_ID_RE.fullmatch(session_id):
            raise InvalidSessionIdError(session_id)
        path = self.root / session_id
        # Defence in depth: the pattern check above already makes escape impossible.
        if not path.resolve().is_relative_to(self.root.resolve()):  # pragma: no cover
            raise InvalidSessionIdError(session_id)
        return path

    # -- model publication (under the model lock) ---------------------------------------

    def lock_model(self, session_id: str) -> ModelLock:
        """The session's model lock; use as ``with store.lock_model(sid) as lock:``."""
        directory = self.session_dir(session_id)
        self._require_session(session_id)
        return ModelLock(session_id, directory / LOCK_FILE)

    def stage_model(self, lock: ModelLock, *, max_bytes: int) -> StagedModel:
        """Begin a size-capped, hashed model version; see :class:`StagedModel`."""
        self._require_lock(lock)
        return StagedModel(lock.session_id, self._models_dir(lock.session_id), max_bytes)

    def set_model(self, lock: ModelLock, sha256: str) -> Session:
        """Activate a committed version: the single atomic write that publishes an upload."""
        self._require_lock(lock)
        version = self.model_version(lock.session_id, sha256)
        missing = version.missing_artefacts()
        if missing:
            raise IncompleteModelVersionError(lock.session_id, sha256, missing)
        current = self.get(lock.session_id)
        updated = current.model_copy(update={"status": "model_ready", "model_hash": sha256})
        validated = Session.model_validate(updated.model_dump())
        self._write_session(validated)
        return validated

    def discard_staging(self, lock: ModelLock) -> int:
        """Remove abandoned staging directories; returns how many were removed.

        Requires the lock because, with it held, any staging directory present belongs to an
        upload that no longer exists (a crash or a killed process).
        """
        self._require_lock(lock)
        models_dir = self._models_dir(lock.session_id)
        if not models_dir.is_dir():
            return 0
        removed = 0
        for child in models_dir.iterdir():
            if child.name.startswith(STAGING_PREFIX) and child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
                if not child.exists():
                    removed += 1
        return removed

    def prune_model_versions(self, lock: ModelLock, *, keep: Iterable[str] = ()) -> list[str]:
        """Delete complete versions other than the active one and ``keep``; returns the hashes.

        Deletion is best-effort per version: a directory that cannot be removed (for example a
        file still being streamed on Windows) is left for a later prune.
        """
        self._require_lock(lock)
        retained = set(keep)
        active = self.get(lock.session_id).model_hash
        if active is not None:
            retained.add(active)
        removed: list[str] = []
        for sha256 in self.list_model_versions(lock.session_id):
            if sha256 in retained:
                continue
            directory = self._models_dir(lock.session_id) / sha256
            shutil.rmtree(directory, ignore_errors=True)
            if not directory.exists():
                removed.append(sha256)
        return removed

    # -- recovery -----------------------------------------------------------------------

    def sweep_staging(self, session_id: str) -> int | None:
        """Remove abandoned staging directories if the session is idle; ``None`` when busy."""
        try:
            with self.lock_model(session_id) as lock:
                return self.discard_staging(lock)
        except ModelLockedError:
            return None

    def sweep_all_staging(self) -> int:
        """Startup recovery: sweep every idle session; returns the number of directories removed."""
        removed = 0
        for session_id in self.session_ids():
            count = self.sweep_staging(session_id)
            if count is None:
                logger.info("session %s busy; staging sweep skipped", session_id)
            else:
                removed += count
        return removed

    # -- model reads --------------------------------------------------------------------

    def model_version(self, session_id: str, sha256: str) -> ModelVersion:
        """Handle to a version directory by hash; existence is not checked."""
        if not _SHA256_RE.fullmatch(sha256):
            raise ValueError("A model version is addressed by its lower-case SHA-256 hex digest.")
        return ModelVersion(session_id, sha256, self._models_dir(session_id) / sha256)

    def active_model(self, session_id: str) -> ModelVersion:
        """The version ``session.json`` points at. Everything a reader needs is inside it."""
        session = self.get(session_id)
        if session.model_hash is None:
            raise ArtefactNotFoundError(session_id, MODEL_FILE)
        version = self.model_version(session_id, session.model_hash)
        missing = version.missing_artefacts()
        if missing:
            raise IncompleteModelVersionError(session_id, session.model_hash, missing)
        return version

    def has_model(self, session_id: str) -> bool:
        try:
            self.active_model(session_id)
        except ArtefactNotFoundError:
            return False
        return True

    def read_model_bytes(self, session_id: str) -> bytes:
        return self.active_model(session_id).read_bytes()

    def list_model_versions(self, session_id: str) -> list[str]:
        """Hashes of the complete versions on disk, active or not, in sorted order."""
        models_dir = self._models_dir(session_id)
        if not models_dir.is_dir():
            return []
        return sorted(
            child.name
            for child in models_dir.iterdir()
            if _SHA256_RE.fullmatch(child.name)
            and ModelVersion(session_id, child.name, child).is_complete
        )

    def staging_directories(self, session_id: str) -> list[Path]:
        models_dir = self._models_dir(session_id)
        if not models_dir.is_dir():
            return []
        return sorted(p for p in models_dir.iterdir() if p.name.startswith(STAGING_PREFIX))

    # -- internals ----------------------------------------------------------------------

    def _models_dir(self, session_id: str) -> Path:
        directory = self.session_dir(session_id)
        self._require_session(session_id)
        return directory / MODELS_DIR

    def _require_session(self, session_id: str) -> None:
        if not (self.root / session_id / SESSION_FILE).is_file():
            raise SessionNotFoundError(session_id)

    def _require_lock(self, lock: ModelLock) -> None:
        if not lock.held:
            raise StorageError("The session's model lock must be held for this operation.")
        self._require_session(lock.session_id)

    def _write_session(self, session: Session) -> None:
        path = self.root / session.id / SESSION_FILE
        self._atomic_write_text(path, canonical_json(session.model_dump(mode="json")))

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        temp = path.with_name(f"{path.name}.{uuid.uuid4().hex}{_TEMP_SUFFIX}")
        try:
            _write_file(temp, text.encode("utf-8"))
            _replace(temp, path)
        except OSError as exc:
            temp.unlink(missing_ok=True)
            raise StorageError(f"Could not write {path.name!r}.") from exc
