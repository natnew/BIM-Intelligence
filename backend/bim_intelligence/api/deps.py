"""Request-scoped dependencies."""

from __future__ import annotations

from fastapi import Depends

from bim_intelligence.config import Settings, get_settings
from bim_intelligence.store import SessionStore

SESSIONS_DIR = "sessions"


def get_store(settings: Settings = Depends(get_settings)) -> SessionStore:
    """A store rooted at ``DATA_DIR/sessions``. Stateless, so one per request is fine."""
    return SessionStore(settings.data_dir / SESSIONS_DIR)
