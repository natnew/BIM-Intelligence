"""Requirements: how a session's reviewable requirements come into being (ARCHITECTURE §9).

This slice implements the IDS path (FR-REQ-05). Narrative document extraction and interactive
confirmation (FR-REQ-01..04) are later tasks and will live beside it.
"""

from bim_intelligence.requirements.ids_import import (
    CONFIRMED_BY_IDS_IMPORT,
    IdsImportResult,
    executable_requirements,
    import_ids_document,
    requirements_for_document,
)
from bim_intelligence.validation import InvalidIdsError

__all__ = [
    "CONFIRMED_BY_IDS_IMPORT",
    "IdsImportResult",
    "InvalidIdsError",
    "executable_requirements",
    "import_ids_document",
    "requirements_for_document",
]
