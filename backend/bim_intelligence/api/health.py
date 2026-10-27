"""Liveness and configuration summary (ARCHITECTURE.md §11, §15).

The response deliberately contains no secret material: it reports whether an
API key is configured, never its value (AGENTS.md §8).
"""

from __future__ import annotations

from importlib import metadata

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from bim_intelligence import __version__
from bim_intelligence.config import LLMMode, Settings, get_settings

router = APIRouter(tags=["health"])


class LibraryVersions(BaseModel):
    """Versions of the openBIM libraries the deterministic pipeline depends on."""

    ifcopenshell: str | None = None
    ifctester: str | None = None


class HealthResponse(BaseModel):
    """Liveness payload. Safe to expose: no credentials or configuration values."""

    status: str = Field(examples=["ok"])
    version: str
    llm_mode: LLMMode
    llm_model: str
    llm_configured: bool = Field(description="True when an API key is present; never the key.")
    libraries: LibraryVersions


def _dist_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness check",
    description="Reports service version, LLM mode and library versions. Never echoes secrets.",
)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        llm_mode=settings.llm_mode,
        llm_model=settings.llm_model,
        llm_configured=settings.has_api_key,
        libraries=LibraryVersions(
            ifcopenshell=_dist_version("ifcopenshell"),
            ifctester=_dist_version("ifctester"),
        ),
    )
