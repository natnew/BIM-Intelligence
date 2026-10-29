"""Requirement document upload (FR-REQ-01, FR-REQ-05).

This slice accepts IDS 1.0 files only; each specification becomes a confirmed requirement.
Narrative documents (BEP as Markdown, text or PDF) are a later task and will share this route.
"""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath, PureWindowsPath

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile

from bim_intelligence.api.deps import get_store
from bim_intelligence.api.errors import problem_responses
from bim_intelligence.bim import UnsupportedUploadError
from bim_intelligence.config import Settings, get_settings
from bim_intelligence.requirements import import_ids_document
from bim_intelligence.schemas import DocumentImport, DocumentKind
from bim_intelligence.store import (
    DocumentNotFoundError,
    SessionStore,
    StorageError,
    UploadTooLargeError,
)

router = APIRouter(tags=["requirements"])

ALLOWED_DOCUMENT_EXTENSIONS: frozenset[str] = frozenset({".ids", ".md", ".txt"})


@router.post(
    "/sessions/{session_id}/documents",
    status_code=201,
    response_model=DocumentImport,
    summary="Upload a requirements document",
    description=(
        "Accepts IDS 1.0 (``.ids``), UTF-8 text (``.txt``) or Markdown (``.md``). IDS is "
        "validated and its specifications become confirmed requirements. Narrative text is "
        "stored byte-for-byte as an untrusted source only; it creates no requirements until "
        "separate interpretation and explicit confirmation. Uploading the same bytes again is "
        "idempotent. Invalid content is 422, other file types are 415, and files above "
        "``MAX_DOC_MB`` are 413. While an upload or review holds the session lock, the request "
        "is refused with 409 ``model-locked``. The client filename is used only for extension "
        "validation."
    ),
    responses={
        200: {"model": DocumentImport, "description": "Document already imported; unchanged."},
        **problem_responses(400, 404, 409, 413, 415, 422),
    },
)
def upload_document(
    session_id: str,
    request: Request,
    response: Response,
    file: UploadFile = File(description="The requirements document: .ids, .md or .txt."),
    store: SessionStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> DocumentImport:
    store.get(session_id)
    kind = _document_kind(file.filename)
    max_bytes = settings.max_doc_mb * 1024 * 1024
    data = _read_capped(file, max_bytes)
    if kind == "ids":
        result = import_ids_document(store, session_id, data, max_bytes=max_bytes)
        document = result.document
        created = result.created
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=422,
                detail="Narrative requirements documents must be valid UTF-8 text.",
            ) from None
        if not text.strip() or "\x00" in text:
            raise HTTPException(
                status_code=422,
                detail="Narrative requirements documents must contain non-empty plain text.",
            )
        with store.lock_model(session_id) as lock:
            expected_hash = hashlib.sha256(data).hexdigest()
            try:
                previous = store.read_document(session_id, expected_hash, kind)
            except DocumentNotFoundError:
                already_registered = False
            else:
                if previous != data:
                    raise StorageError("Stored narrative document failed integrity check.")
                already_registered = True
            document_id = store.add_document(lock, data, kind)
        document = DocumentImport(
            sha256=document_id,
            kind=kind,
            title="Narrative requirements document",
            requirements=[],
        )
        created = not already_registered
    response.status_code = 201 if created else 200
    response.headers["Location"] = request.url_for("list_requirements", session_id=session_id).path
    return document


def _document_kind(filename: str | None) -> DocumentKind:
    if filename is None:
        raise UnsupportedUploadError(filename, ALLOWED_DOCUMENT_EXTENSIONS)
    leaf = PurePosixPath(PureWindowsPath(filename).name).name
    extension = PurePosixPath(leaf).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise UnsupportedUploadError(filename, ALLOWED_DOCUMENT_EXTENSIONS)
    kinds: dict[str, DocumentKind] = {
        ".ids": "ids",
        ".txt": "text",
        ".md": "markdown",
    }
    return kinds[extension]


def _read_capped(upload: UploadFile, max_bytes: int) -> bytes:
    # One byte past the cap is enough to know the upload is too large without holding it all.
    data = upload.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise UploadTooLargeError(max_bytes)
    return data
