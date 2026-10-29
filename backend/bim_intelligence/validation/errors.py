"""Exceptions raised by the ``validation`` package. Messages never contain file-system paths."""

from __future__ import annotations


class IdsError(Exception):
    """Base class for IDS import and execution failures."""


class InvalidIdsError(IdsError):
    """The document is not a well-formed, XSD-valid IDS 1.0 file (ARCHITECTURE §14: 422)."""


class CheckSpecIntegrityError(IdsError):
    """A ``CheckSpec`` cannot be executed as stored: wrong kind, or payload and version disagree.

    Raised by hydration and reported by the runner as ``CheckResult.status="error"`` so that a
    tampered or corrupted specification can never run as a weaker check (C-02).
    """
