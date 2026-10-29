"""RFC 9457 error envelope for every endpoint (ARCHITECTURE §14).

Domain exceptions from ``store/``, ``bim/``, ``requirements/`` and ``orchestration/`` are mapped
here, once, to a status code and a stable problem type. Handlers never echo file-system paths:
domain messages are written without them, and storage failures are reported generically and
logged server-side.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from bim_intelligence.api.correlation import correlation_id_from_scope
from bim_intelligence.bim import (
    AmbiguousGlobalIdError,
    IfcLoadError,
    InvalidGlobalIdError,
    UnknownElementError,
    UnsupportedSchemaError,
    UnsupportedUploadError,
)
from bim_intelligence.orchestration import NoExecutableChecksError
from bim_intelligence.requirements import InvalidIdsError
from bim_intelligence.schemas import ProblemDetail
from bim_intelligence.store import (
    ArtefactNotFoundError,
    DocumentNotFoundError,
    InvalidRunIdError,
    InvalidSessionIdError,
    ModelLockedError,
    ModelVersionMismatchError,
    RunNotFoundError,
    SessionNotFoundError,
    StorageError,
    UploadTooLargeError,
)

logger = logging.getLogger(__name__)

PROBLEM_MEDIA_TYPE = "application/problem+json"
# Mirrors the ``$id`` convention used for the exported schema bundle: a stable, project-scoped
# URI namespace rather than a resolvable document.
PROBLEM_TYPE_BASE = "https://github.com/natnew/BIM-Intelligence/problems/"


@dataclass(frozen=True)
class ProblemSpec:
    status: int
    slug: str
    title: str
    expose_detail: bool = True

    @property
    def type_uri(self) -> str:
        return PROBLEM_TYPE_BASE + self.slug


# Order is irrelevant: FastAPI resolves handlers by the exception's MRO, so a subclass
# (UnsupportedSchemaError) wins over its base (IfcLoadError).
DOMAIN_PROBLEMS: dict[type[Exception], ProblemSpec] = {
    InvalidSessionIdError: ProblemSpec(400, "invalid-session-id", "Invalid session id"),
    SessionNotFoundError: ProblemSpec(404, "session-not-found", "Session not found"),
    ArtefactNotFoundError: ProblemSpec(404, "model-not-found", "Model not uploaded"),
    ModelLockedError: ProblemSpec(409, "model-locked", "Model locked by another operation"),
    UploadTooLargeError: ProblemSpec(413, "upload-too-large", "Upload too large"),
    UnsupportedUploadError: ProblemSpec(415, "unsupported-upload", "Unsupported upload"),
    UnsupportedSchemaError: ProblemSpec(422, "unsupported-ifc-schema", "Unsupported IFC schema"),
    IfcLoadError: ProblemSpec(422, "ifc-unreadable", "IFC could not be parsed"),
    InvalidGlobalIdError: ProblemSpec(400, "invalid-global-id", "Invalid GlobalId"),
    UnknownElementError: ProblemSpec(404, "element-not-found", "Element not found"),
    AmbiguousGlobalIdError: ProblemSpec(409, "ambiguous-global-id", "Ambiguous GlobalId"),
    ModelVersionMismatchError: ProblemSpec(412, "model-version-mismatch", "Model version mismatch"),
    InvalidIdsError: ProblemSpec(422, "ids-invalid", "IDS document invalid"),
    InvalidRunIdError: ProblemSpec(400, "invalid-run-id", "Invalid run id"),
    RunNotFoundError: ProblemSpec(404, "run-not-found", "Review run not found"),
    DocumentNotFoundError: ProblemSpec(404, "document-not-found", "Document not found"),
    NoExecutableChecksError: ProblemSpec(
        409, "no-executable-checks", "No confirmed requirements to review"
    ),
    StorageError: ProblemSpec(500, "storage-failure", "Storage failure", expose_detail=False),
}
REQUEST_VALIDATION = ProblemSpec(422, "request-validation", "Request validation failed")

_GENERIC_STORAGE_DETAIL = "The server could not read or write session storage."


def problem_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI ``responses`` entries documenting the ProblemDetail shape for error codes."""
    return {
        status: {
            "model": ProblemDetail,
            "description": HTTPStatus(status).phrase,
            "content": {PROBLEM_MEDIA_TYPE: {"schema": ProblemDetail.model_json_schema()}},
        }
        for status in statuses
    }


def problem_response(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str | None,
    type_uri: str = "about:blank",
) -> JSONResponse:
    problem = ProblemDetail(
        type=type_uri,
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
        correlation_id=correlation_id_from_scope(request.scope),
    )
    return JSONResponse(
        status_code=status, content=problem.model_dump(mode="json"), media_type=PROBLEM_MEDIA_TYPE
    )


def register_exception_handlers(app: FastAPI) -> None:
    for exc_type, spec in DOMAIN_PROBLEMS.items():
        app.add_exception_handler(exc_type, _domain_handler(spec))
    app.add_exception_handler(RequestValidationError, _request_validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)


def _domain_handler(spec: ProblemSpec) -> Any:
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        if spec.expose_detail:
            detail = str(exc)
        else:
            logger.error("%s on %s: %s", spec.title, request.url.path, exc, exc_info=exc)
            detail = _GENERIC_STORAGE_DETAIL
        return problem_response(
            request, status=spec.status, title=spec.title, detail=detail, type_uri=spec.type_uri
        )

    return handler


async def _request_validation_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    messages = [
        f"{'.'.join(str(part) for part in err.get('loc', ()))}: {err.get('msg', 'invalid')}"
        for err in exc.errors()
    ]
    return problem_response(
        request,
        status=REQUEST_VALIDATION.status,
        title=REQUEST_VALIDATION.title,
        detail="; ".join(messages) or None,
        type_uri=REQUEST_VALIDATION.type_uri,
    )


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    try:
        title = HTTPStatus(exc.status_code).phrase
    except ValueError:
        title = "Error"
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail != title else None
    response = problem_response(request, status=exc.status_code, title=title, detail=detail)
    for name, value in (exc.headers or {}).items():
        response.headers[name] = value
    return response
