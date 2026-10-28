"""Open an IFC file read-only and confirm its schema (FR-ING-01, ADR-004).

IfcOpenShell is lenient: a truncated DATA section still opens. What it does reject — an
unreadable file, a non-STEP header or an unknown ``FILE_SCHEMA`` — is surfaced here as
``IfcLoadError`` / ``UnsupportedSchemaError`` with any storage path scrubbed from the message.
"""

from __future__ import annotations

from pathlib import Path

import ifcopenshell

from bim_intelligence.bim.errors import IfcLoadError, UnsupportedSchemaError

SUPPORTED_SCHEMAS: frozenset[str] = frozenset({"IFC2X3", "IFC4", "IFC4X3"})
_PATH_PLACEHOLDER = "<model>"


def open_ifc(path: Path) -> ifcopenshell.file:
    """Parse ``path`` with IfcOpenShell. The file is never modified or re-saved (C-04)."""
    if not path.is_file():
        raise IfcLoadError("The model file does not exist.")
    try:
        model = ifcopenshell.open(str(path))
    except ifcopenshell.SchemaError as exc:
        raise UnsupportedSchemaError(_schema_from_message(str(exc)), SUPPORTED_SCHEMAS) from exc
    except (ifcopenshell.Error, OSError, RuntimeError, ValueError) as exc:
        raise IfcLoadError(
            f"IfcOpenShell could not parse the file: {_scrub(str(exc), path)}"
        ) from exc
    schema = str(model.schema)
    if schema not in SUPPORTED_SCHEMAS:
        raise UnsupportedSchemaError(schema, SUPPORTED_SCHEMAS)
    return model


def _scrub(message: str, path: Path) -> str:
    for candidate in {str(path), path.as_posix(), path.name}:
        if candidate:
            message = message.replace(candidate, _PATH_PLACEHOLDER)
    return message or "unreadable input"


def _schema_from_message(message: str) -> str:
    # IfcOpenShell reports "Unsupported schema: IFC9X9"; fall back to the raw text.
    _, sep, schema = message.partition(":")
    return schema.strip() if sep else message.strip()
