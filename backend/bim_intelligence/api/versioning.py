"""Binding every model read to one version (ADR-017).

A handler resolves the session's active :class:`ModelVersion` once and reads bytes, index and
summary only from that immutable directory, so one response can never mix versions. Across
requests the client holds the version in the ``ETag`` (the quoted SHA-256) and may assert it
with ``If-Match``; a mismatch is 412 ``model-version-mismatch`` rather than a silent switch to
whatever model was uploaded in between. The error type lives in ``store`` so that the review
runner can raise it too; it is re-exported here for the API layer.
"""

from __future__ import annotations

from fastapi import Request

from bim_intelligence.store import ModelVersion, ModelVersionMismatchError, SessionStore

IF_MATCH_HEADER = "If-Match"
MODEL_CACHE_CONTROL = "private, no-cache"

__all__ = [
    "IF_MATCH_HEADER",
    "MODEL_CACHE_CONTROL",
    "ModelVersionMismatchError",
    "etag_for",
    "etag_matches",
    "if_match_sha256",
    "resolve_model_version",
]


def etag_for(version: ModelVersion) -> str:
    return f'"{version.sha256}"'


def resolve_model_version(store: SessionStore, session_id: str, request: Request) -> ModelVersion:
    """The active version, after honouring an ``If-Match`` precondition if the client sent one."""
    version = store.active_model(session_id)
    if_match = request.headers.get("if-match")
    if if_match is not None and not etag_matches(if_match, etag_for(version), weak=False):
        raise ModelVersionMismatchError(session_id, if_match.strip(), etag_for(version))
    return version


def if_match_sha256(request: Request) -> str | None:
    """The single strong entity-tag an ``If-Match`` header pins, as a bare SHA-256, if any.

    Used where the precondition must be re-checked under a lock by code that cannot see the
    request. ``*`` and absent headers pin nothing; anything else is passed through verbatim so a
    malformed tag fails the comparison instead of silently matching.
    """
    header = request.headers.get("if-match")
    if header is None:
        return None
    candidates = [value.strip() for value in header.split(",")]
    if "*" in candidates:
        return None
    if len(candidates) == 1 and candidates[0].startswith('"') and candidates[0].endswith('"'):
        return candidates[0][1:-1]
    return header.strip()


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
