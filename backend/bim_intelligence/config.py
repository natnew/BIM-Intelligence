"""Application configuration.

All settings come from environment variables (or a local ``.env`` file). The
validators here enforce the security defaults described in ARCHITECTURE.md §13:
Standard-mode model identifiers only (ADR-010, NFR-08) and loopback binding
unless remote access is explicitly allowed.
"""

from __future__ import annotations

import ipaddress
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class ConfigurationError(ValueError):
    """Raised when the environment describes an unsafe or inconsistent configuration."""


class LLMMode(str, Enum):
    """How the backend talks to the language model."""

    LIVE = "live"
    REPLAY = "replay"
    OFF = "off"


CONTRIBUTOR_SUFFIX = "-contributor"
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class Settings(BaseSettings):
    """Runtime settings. Field names match the variables documented in ``.env.example``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Meta Model API
    model_api_key: SecretStr | None = Field(default=None, description="Meta Model API key.")
    llm_base_url: str = "https://api.meta.ai/v1"
    llm_model: str = "muse-spark-1.3"
    llm_mode: LLMMode = LLMMode.OFF
    llm_recordings_dir: Path = Path("tests/evaluation/recordings")
    allow_contributor_models: bool = False
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_max_retries: int = Field(default=2, ge=0, le=5)

    # Orchestration limits (NFR-05, NFR-06)
    max_tool_calls_per_run: int = Field(default=12, ge=1, le=100)
    max_plan_checks: int = Field(default=10, ge=1, le=50)
    max_input_tokens_per_run: int = Field(default=150_000, ge=1_000)

    # Cost estimation (USD per 1M tokens; indicative)
    llm_price_input_per_m: float = Field(default=1.25, ge=0)
    llm_price_output_per_m: float = Field(default=4.25, ge=0)

    # Server
    bimi_host: str = "127.0.0.1"
    bimi_port: int = Field(default=8000, ge=1, le=65535)
    allow_remote: bool = False
    # NoDecode: parsed as a comma-separated string, not JSON (see _split_origins).
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    # Storage and upload limits
    data_dir: Path = Path("data")
    max_ifc_mb: int = Field(default=200, ge=1)
    max_doc_mb: int = Field(default=25, ge=1)

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("llm_model")
    @classmethod
    def _non_empty_model(cls, value: str) -> str:
        if not value.strip():
            raise ConfigurationError("LLM_MODEL must not be empty.")
        return value.strip()

    @model_validator(mode="after")
    def _reject_contributor_models(self) -> Settings:
        """Contributor-mode ids permit Meta to train on submitted content (ADR-010)."""
        if self.llm_model.endswith(CONTRIBUTOR_SUFFIX) and not self.allow_contributor_models:
            raise ConfigurationError(
                f"LLM_MODEL={self.llm_model!r} is a Contributor-mode identifier, which allows "
                "uploaded project data to be used for model training. Use a Standard-mode id "
                "(e.g. 'muse-spark-1.3') or set ALLOW_CONTRIBUTOR_MODELS=true with explicit "
                "approval."
            )
        return self

    @model_validator(mode="after")
    def _require_key_for_live_mode(self) -> Settings:
        if self.llm_mode is LLMMode.LIVE and not self.has_api_key:
            raise ConfigurationError("LLM_MODE=live requires MODEL_API_KEY to be set.")
        return self

    @model_validator(mode="after")
    def _guard_remote_binding(self) -> Settings:
        """Uploaded project files must not be exposed on a network interface by accident."""
        if not self.allow_remote and not _is_loopback(self.bimi_host):
            raise ConfigurationError(
                f"BIMI_HOST={self.bimi_host!r} is not a loopback address. "
                "Set ALLOW_REMOTE=true to bind to a non-local interface deliberately."
            )
        return self

    @property
    def has_api_key(self) -> bool:
        return self.model_api_key is not None and bool(self.model_api_key.get_secret_value())

    @property
    def llm_enabled(self) -> bool:
        return self.llm_mode is not LLMMode.OFF


def _is_loopback(host: str) -> bool:
    if host in LOOPBACK_HOSTS:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings, loaded once. Tests call ``get_settings.cache_clear()``."""
    return Settings()
