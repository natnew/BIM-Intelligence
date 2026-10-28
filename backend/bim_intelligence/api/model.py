"""Model upload, summary and read-only file download (FR-ING-01..03, C-07).

Handlers are synchronous ``def`` so FastAPI runs them in its threadpool: IfcOpenShell parsing
and indexing must not block the event loop (BAKEOFF review §7.2 step 5).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import PurePosixPath, PureWindowsPath

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from fastapi.responses import FileResponse

from bim_intelligence.api.deps import get_store
from bim_intelligence.api.errors import problem_responses
from bim_intelligence.bim import UnsupportedUploadError, ingest_model, load_summary
from bim_intelligence.config import Settings, get_settings
from bim_intelligence.schemas import ModelSummary
from bim_intelligence.store import MODEL_FILE, ArtefactNotFoundError, SessionStore

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
        "byte-for-byte under a fixed name, builds the Model Index and returns the ModelSummary. "
        "Re-uploading replaces the session's model; a rejected upload leaves the previous model "
        "in place. The client filename is used only for the extension check."
    ),
    responses=problem_responses(400, 404, 413, 415, 422),
)
def upload_model(
    session_id: str,
    file: UploadFile = File(description="The IFC file. Only the .ifc extension is accepted."),
    store: SessionStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> ModelSummary:
    store.get(session_id)
    _require_allowed_extension(file.filename)
    max_bytes = settings.max_ifc_mb * 1024 * 1024
    index = ingest_model(store, session_id, _chunks(file), max_bytes=max_bytes)
    return index.summary


@router.get(
    "/sessions/{session_id}/model/summary",
    response_model=ModelSummary,
    summary="Model summary",
    description="Schema, hash, project name, instance counts per IFC class and storeys.",
    responses=problem_responses(400, 404),
)
def get_model_summary(session_id: str, store: SessionStore = Depends(get_store)) -> ModelSummary:
    return load_summary(store, session_id)


@router.get(
    "/sessions/{session_id}/model/file",
    response_class=FileResponse,
    summary="Download the stored IFC",
    description=(
        "Streams the stored model exactly as uploaded (``application/x-step``). ``ETag`` is the "
        "quoted SHA-256 of the bytes; ``If-None-Match`` is honoured with 304. This is the URL "
        "the viewer loads geometry from, so viewer and validator always see the same bytes."
    ),
    responses={
        200: {"content": {IFC_MEDIA_TYPE: {}}, "description": "The stored IFC bytes."},
        304: {"description": "Not modified; the client's ETag matches the stored model."},
        **problem_responses(400, 404),
    },
)
def get_model_file(
    session_id: str, request: Request, store: SessionStore = Depends(get_store)
) -> Response:
    session = store.get(session_id)
    if session.model_hash is None or not store.has_model(session_id):
        raise ArtefactNotFoundError(session_id, MODEL_FILE)
    etag = f'"{session.model_hash}"'
    headers = {"ETag": etag, "Cache-Control": "private, no-cache"}
    if _etag_matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=headers)
    return FileResponse(
        store.path_for(session_id, MODEL_FILE),
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


def _etag_matches(if_none_match: str | None, etag: str) -> bool:
    if not if_none_match:
        return False
    candidates = [value.strip() for value in if_none_match.split(",")]
    return "*" in candidates or any(c.removeprefix("W/") == etag for c in candidates)
