"""Model upload, summary and read-only file download (FR-ING-01..03, C-07, ADR-017).

Handlers are synchronous ``def`` so FastAPI runs them in its threadpool: IfcOpenShell parsing
and indexing must not block the event loop (BAKEOFF review §7.2 step 5). Every read resolves
the active model version once and serves only that version; the version's SHA-256 is the
``ETag`` on each response.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import PurePosixPath, PureWindowsPath

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from fastapi.responses import FileResponse

from bim_intelligence.api.deps import get_store
from bim_intelligence.api.errors import problem_responses
from bim_intelligence.api.versioning import (
    MODEL_CACHE_CONTROL,
    etag_for,
    etag_matches,
    resolve_model_version,
)
from bim_intelligence.bim import UnsupportedUploadError, ingest_model, load_summary
from bim_intelligence.config import Settings, get_settings
from bim_intelligence.schemas import ModelSummary
from bim_intelligence.store import MODEL_FILE, SessionStore

router = APIRouter(tags=["model"])

ALLOWED_MODEL_EXTENSIONS: frozenset[str] = frozenset({".ifc"})
IFC_MEDIA_TYPE = "application/x-step"
UPLOAD_CHUNK_BYTES = 1 << 20


@router.post(
    "/sessions/{session_id}/model",
    status_code=201,
    response_model=ModelSummary,
    summary="Upload and index an IFC model",
    description=(
        "Accepts one ``.ifc`` file (IFC2X3, IFC4 or IFC4X3) as multipart form data, stores it "
        "byte-for-byte, builds the Model Index and returns the ModelSummary. The upload, its "
        "index and its summary are published together as one immutable model version and "
        "become active in a single step; a rejected upload leaves the previous version active "
        "and untouched. Re-uploading replaces the active version. ``ETag`` is the quoted "
        "SHA-256 of the new version. While another upload for the session is in progress the "
        "request is refused with 409 ``model-locked`` rather than queued. The client filename "
        "is used only for the extension check."
    ),
    responses=problem_responses(400, 404, 409, 413, 415, 422),
)
def upload_model(
    session_id: str,
    response: Response,
    file: UploadFile = File(description="The IFC file. Only the .ifc extension is accepted."),
    store: SessionStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> ModelSummary:
    store.get(session_id)
    _require_allowed_extension(file.filename)
    max_bytes = settings.max_ifc_mb * 1024 * 1024
    index = ingest_model(store, session_id, _chunks(file), max_bytes=max_bytes)
    response.headers["ETag"] = f'"{index.summary.model_hash}"'
    return index.summary


@router.get(
    "/sessions/{session_id}/model/summary",
    response_model=ModelSummary,
    summary="Model summary",
    description=(
        "Schema, hash, project name, instance counts per IFC class and storeys of the active "
        "model version. ``ETag`` is the quoted SHA-256; ``If-Match`` with a different value "
        "returns 412 ``model-version-mismatch``."
    ),
    responses=problem_responses(400, 404, 412),
)
def get_model_summary(
    session_id: str,
    request: Request,
    response: Response,
    store: SessionStore = Depends(get_store),
) -> ModelSummary:
    version = resolve_model_version(store, session_id, request)
    response.headers["ETag"] = etag_for(version)
    response.headers["Cache-Control"] = MODEL_CACHE_CONTROL
    return load_summary(version)


@router.get(
    "/sessions/{session_id}/model/file",
    response_class=FileResponse,
    summary="Download the stored IFC",
    description=(
        "Streams the active model version exactly as uploaded (``application/x-step``). "
        "``ETag`` is the quoted SHA-256 of the bytes and always matches the body, because the "
        "file is read from the immutable version directory the hash names. ``If-None-Match`` "
        "is honoured with 304; ``If-Match`` with a different value returns 412. This is the "
        "URL the viewer loads geometry from, so viewer and validator always see the same bytes."
    ),
    responses={
        200: {"content": {IFC_MEDIA_TYPE: {}}, "description": "The stored IFC bytes."},
        304: {"description": "Not modified; the client's ETag matches the active model."},
        **problem_responses(400, 404, 412),
    },
)
def get_model_file(
    session_id: str, request: Request, store: SessionStore = Depends(get_store)
) -> Response:
    version = resolve_model_version(store, session_id, request)
    etag = etag_for(version)
    headers = {"ETag": etag, "Cache-Control": MODEL_CACHE_CONTROL}
    if etag_matches(request.headers.get("if-none-match"), etag, weak=True):
        return Response(status_code=304, headers=headers)
    return FileResponse(
        version.path_for(MODEL_FILE),
        media_type=IFC_MEDIA_TYPE,
        filename=MODEL_FILE,
        headers=headers,
    )


def _require_allowed_extension(filename: str | None) -> None:
    if filename is None:
        raise UnsupportedUploadError(filename, ALLOWED_MODEL_EXTENSIONS)
    # Browsers send bare names, but be defensive about either separator convention.
    leaf = PurePosixPath(PureWindowsPath(filename).name).name
    if PurePosixPath(leaf).suffix.lower() not in ALLOWED_MODEL_EXTENSIONS:
        raise UnsupportedUploadError(filename, ALLOWED_MODEL_EXTENSIONS)


def _chunks(upload: UploadFile) -> Iterator[bytes]:
    while chunk := upload.file.read(UPLOAD_CHUNK_BYTES):
        yield chunk
