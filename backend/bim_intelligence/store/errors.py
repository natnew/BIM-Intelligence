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
