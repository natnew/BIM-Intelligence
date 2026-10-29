"""Requirements: how a session's reviewable requirements come into being (ARCHITECTURE §9)."""

from bim_intelligence.requirements.ids_import import (
    CONFIRMED_BY_IDS_IMPORT,
    IdsImportResult,
    executable_requirements,
    import_ids_document,
    requirements_for_document,
)
from bim_intelligence.requirements.narrative import (
    RequirementInterpretationError,
    confirm_candidate,
    extract_candidates,
    verify_candidate_quote,
)
from bim_intelligence.requirements.native import (
    CONFIRMED_BY_NATIVE_SELECTION,
    NativeRequirementResult,
    confirm_classification_consistency,
)
from bim_intelligence.validation import InvalidIdsError

__all__ = [
    "CONFIRMED_BY_IDS_IMPORT",
    "CONFIRMED_BY_NATIVE_SELECTION",
    "IdsImportResult",
    "InvalidIdsError",
    "NativeRequirementResult",
    "RequirementInterpretationError",
    "confirm_candidate",
    "confirm_classification_consistency",
    "executable_requirements",
    "extract_candidates",
    "import_ids_document",
    "requirements_for_document",
    "verify_candidate_quote",
]
