"""Storage exceptions. Messages never contain file-system paths (ARCHITECTURE §13)."""

from __future__ import annotations


class StorageError(Exception):
    """Base class for every session-store failure."""


class InvalidSessionIdError(StorageError, ValueError):
    """The supplied session id is not a lower-case UUID4."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Invalid session id {session_id!r}: expected a lower-case UUID4.")
        self.session_id = session_id


class SessionNotFoundError(StorageError, LookupError):
    """No session directory with a valid record exists for this id."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session {session_id} does not exist.")
        self.session_id = session_id


class ArtefactNotFoundError(StorageError, LookupError):
    """The session exists but the requested artefact has not been written yet."""

    def __init__(self, session_id: str, artefact: str) -> None:
        super().__init__(f"Session {session_id} has no {artefact!r} yet.")
        self.session_id = session_id
        self.artefact = artefact


class UploadTooLargeError(StorageError):
    """The upload exceeded the configured byte limit."""

    def __init__(self, max_bytes: int) -> None:
        super().__init__(f"Upload exceeds the limit of {max_bytes} bytes.")
        self.max_bytes = max_bytes


class ModelLockedError(StorageError):
    """Another operation holds the session's model lock (an upload or, later, a review run)."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"Session {session_id}: the model is locked by another operation in progress; "
            "retry when it completes."
        )
        self.session_id = session_id


class IncompleteModelVersionError(StorageError):
    """A model version directory lacks one of its artefacts; it is never served or activated."""

    def __init__(self, session_id: str, sha256: str, missing: list[str]) -> None:
        super().__init__(
            f"Session {session_id}: model version {sha256[:12]} is incomplete "
            f"(missing {sorted(missing)})."
        )
        self.session_id = session_id
        self.sha256 = sha256
        self.missing = missing


class ModelVersionMismatchError(Exception):
    """The caller asserted a model version (``If-Match`` or a pinned run) that is not active."""

    def __init__(self, session_id: str, expected: str, active: str) -> None:
        super().__init__(
            f"Session {session_id}: the request requires model version {expected} but the "
            f"active model is {active}. Reload the model before retrying."
        )
        self.session_id = session_id
        self.expected = expected
        self.active = active


class DocumentNotFoundError(StorageError, LookupError):
    """No stored document with this hash and kind exists in the session."""

    def __init__(self, session_id: str, sha256: str, kind: str) -> None:
        super().__init__(f"Session {session_id} has no {kind} document {sha256[:12]}.")
        self.session_id = session_id
        self.sha256 = sha256
        self.kind = kind


class InvalidRunIdError(StorageError, ValueError):
    """The supplied run id is not a lower-case UUID4."""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Invalid run id {run_id!r}: expected a lower-case UUID4.")
        self.run_id = run_id


class RunNotFoundError(StorageError, LookupError):
    """No published review run with this id exists in the session."""

    def __init__(self, session_id: str, run_id: str) -> None:
        super().__init__(f"Session {session_id} has no review run {run_id}.")
        self.session_id = session_id
        self.run_id = run_id
