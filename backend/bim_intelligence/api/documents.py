"""Requirement document upload (FR-REQ-01, FR-REQ-05).

This slice accepts IDS 1.0 files only; each specification becomes a confirmed requirement.
Narrative documents (BEP as Markdown, text or PDF) are a later task and will share this route.
"""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile

from bim_intelligence.api.deps import get_store
from bim_intelligence.api.errors import problem_responses
from bim_intelligence.bim import UnsupportedUploadError
from bim_intelligence.config import Settings, get_settings
from bim_intelligence.requirements import import_ids_document
from bim_intelligence.schemas import DocumentImport
from bim_intelligence.store import SessionStore, UploadTooLargeError

router = APIRouter(tags=["requirements"])

ALLOWED_DOCUMENT_EXTENSIONS: frozenset[str] = frozenset({".ids"})


@router.post(
    "/sessions/{session_id}/documents",
    status_code=201,
    response_model=DocumentImport,
    summary="Upload a requirements document",
    description=(
        "Accepts one IDS 1.0 file (``.ids``) as multipart form data. The document is validated "
        "against the IDS 1.0 XML Schema, stored byte-for-byte under its SHA-256 and registered "
        "on the session; every ``<specification>`` becomes a confirmed ``Requirement`` bound to "
        "an immutable ``CheckSpec``. Uploading the same bytes again returns the requirements "
        "created the first time with status 200 instead of 201. Invalid or malformed IDS "
        "content is 422 ``ids-invalid``; other file types are 415; files above ``MAX_DOC_MB`` "
        "are 413. While an upload or a review holds the session's lock the request is refused "
        "with 409 ``model-locked``. The client filename is used only for the extension check."
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
    file: UploadFile = File(description="The IDS file. Only the .ids extension is accepted."),
    store: SessionStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> DocumentImport:
    store.get(session_id)
    _require_allowed_extension(file.filename)
    max_bytes = settings.max_doc_mb * 1024 * 1024
    data = _read_capped(file, max_bytes)
    result = import_ids_document(store, session_id, data, max_bytes=max_bytes)
    response.status_code = 201 if result.created else 200
    response.headers["Location"] = request.url_for("list_requirements", session_id=session_id).path
    return result.document


def _require_allowed_extension(filename: str | None) -> None:
    if filename is None:
        raise UnsupportedUploadError(filename, ALLOWED_DOCUMENT_EXTENSIONS)
    leaf = PurePosixPath(PureWindowsPath(filename).name).name
    if PurePosixPath(leaf).suffix.lower() not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise UnsupportedUploadError(filename, ALLOWED_DOCUMENT_EXTENSIONS)


def _read_capped(upload: UploadFile, max_bytes: int) -> bytes:
    # One byte past the cap is enough to know the upload is too large without holding it all.
    data = upload.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise UploadTooLargeError(max_bytes)
    return data
