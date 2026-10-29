"""Binding every model read to one version (ADR-017).

A handler resolves the session's active :class:`ModelVersion` once and reads bytes, index and
summary only from that immutable directory, so one response can never mix versions. Across
requests the client holds the version in the ``ETag`` (the quoted SHA-256) and may assert it
with ``If-Match``; a mismatch is 412 ``model-version-mismatch`` rather than a silent switch to
whatever model was uploaded in between.
"""

from __future__ import annotations

from fastapi import Request

from bim_intelligence.store import ModelVersion, SessionStore

IF_MATCH_HEADER = "If-Match"
MODEL_CACHE_CONTROL = "private, no-cache"


class ModelVersionMismatchError(Exception):
    """The client asserted a model version (``If-Match``) that is no longer the active one."""

    def __init__(self, session_id: str, expected: str, active: str) -> None:
        super().__init__(
            f"Session {session_id}: the request requires model version {expected} but the "
            f"active model is {active}. Reload the model before retrying."
        )
        self.session_id = session_id
        self.expected = expected
        self.active = active


def etag_for(version: ModelVersion) -> str:
    return f'"{version.sha256}"'


def resolve_model_version(store: SessionStore, session_id: str, request: Request) -> ModelVersion:
    """The active version, after honouring an ``If-Match`` precondition if the client sent one."""
    version = store.active_model(session_id)
    if_match = request.headers.get("if-match")
    if if_match is not None and not etag_matches(if_match, etag_for(version), weak=False):
        raise ModelVersionMismatchError(session_id, if_match.strip(), etag_for(version))
    return version


def etag_matches(header: str | None, etag: str, *, weak: bool) -> bool:
    """RFC 9110 entity-tag comparison. ``If-Match`` is strong; ``If-None-Match`` may be weak."""
    if not header:
        return False
    candidates = [value.strip() for value in header.split(",")]
    if "*" in candidates:
        return True
    if weak:
        return any(c.removeprefix("W/") == etag for c in candidates)
    return etag in candidates
