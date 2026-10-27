"""FastAPI application factory.

Run locally with::

    uvicorn bim_intelligence.api.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bim_intelligence import __version__
from bim_intelligence.api.health import router as health_router
from bim_intelligence.config import Settings, get_settings

API_PREFIX = "/api/v1"


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
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    app.include_router(health_router, prefix=API_PREFIX)
    # Routers resolve settings through this dependency; binding it here means the
    # instance passed to create_app() is the one actually used (tests rely on this).
    app.dependency_overrides[get_settings] = lambda: settings
    return app


app = create_app()
