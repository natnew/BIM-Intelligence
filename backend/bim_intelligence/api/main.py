"""FastAPI application factory.

Run locally with::

    uvicorn bim_intelligence.api.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bim_intelligence import __version__
from bim_intelligence.api.budget import router as budget_router
from bim_intelligence.api.correlation import CORRELATION_HEADER, CorrelationIdMiddleware
from bim_intelligence.api.deps import SESSIONS_DIR
from bim_intelligence.api.documents import router as documents_router
from bim_intelligence.api.elements import router as elements_router
from bim_intelligence.api.errors import register_exception_handlers
from bim_intelligence.api.findings import router as findings_router
from bim_intelligence.api.health import router as health_router
from bim_intelligence.api.model import router as model_router
from bim_intelligence.api.requirements import router as requirements_router
from bim_intelligence.api.reviews import router as reviews_router
from bim_intelligence.api.sessions import router as sessions_router
from bim_intelligence.api.versioning import IF_MATCH_HEADER
from bim_intelligence.config import Settings, get_settings
from bim_intelligence.store import SessionStore, StorageError

API_PREFIX = "/api/v1"
# Conditional-request headers are not CORS-safelisted; without this the frontend could not pin
# reads to a model version (ADR-017 §3). Regression test: tests/unit/api/test_cors.py.
CORS_ALLOWED_HEADERS = ("Content-Type", CORRELATION_HEADER, IF_MATCH_HEADER, "If-None-Match")
ROUTERS = (
    health_router,
    budget_router,
    sessions_router,
    model_router,
    elements_router,
    documents_router,
    requirements_router,
    reviews_router,
    findings_router,
)

logger = logging.getLogger(__name__)


def _lifespan_for(settings: Settings) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Recovery after an interrupted upload (ADR-017): staging directories belong to no
        # live request once the process has restarted, so remove them before serving.
        try:
            removed = SessionStore(settings.data_dir / SESSIONS_DIR).sweep_all_staging()
        except (StorageError, OSError) as exc:
            logger.warning("startup staging sweep failed: %s", exc)
        else:
            if removed:
                logger.info("removed %d abandoned staging director(ies)", removed)
        yield

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Tests pass explicit settings; production reads the environment."""
    settings = settings or get_settings()

    app = FastAPI(
        title="BIM Intelligence API",
        version=__version__,
        description=(
            "AI-native architectural BIM review. Deterministic IFC validation with "
            "Muse Spark-assisted requirement interpretation and grounded explanation."
        ),
        docs_url=f"{API_PREFIX}/docs",
        openapi_url=f"{API_PREFIX}/openapi.json",
        lifespan=_lifespan_for(settings),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=list(CORS_ALLOWED_HEADERS),
        expose_headers=["ETag", CORRELATION_HEADER],
    )
    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)
    for router in ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    # Routers resolve settings through this dependency; binding it here means the
    # instance passed to create_app() is the one actually used (tests rely on this).
    app.dependency_overrides[get_settings] = lambda: settings
    return app


app = create_app()
