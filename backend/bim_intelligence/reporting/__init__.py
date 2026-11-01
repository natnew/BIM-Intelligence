"""Reporting and separately labelled, evidence-grounded explanation services."""

from bim_intelligence.reporting.explanations import (
    ExplanationProvenanceError,
    FindingNotInRunError,
    GroundingError,
    RunModelMismatchError,
    deterministic_explanation,
    explain_finding,
    resolve_finding_provenance,
    verify_index_provenance,
)

__all__ = [
    "ExplanationProvenanceError",
    "FindingNotInRunError",
    "GroundingError",
    "RunModelMismatchError",
    "deterministic_explanation",
    "explain_finding",
    "resolve_finding_provenance",
    "verify_index_provenance",
]
