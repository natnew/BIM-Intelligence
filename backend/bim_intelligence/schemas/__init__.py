"""Domain models shared by every component and exported to the frontend (C-07, ADR-014).

Terminology is fixed here: *Session*, *ElementRef*, *ElementRecord*, *ModelSummary*,
*Requirement*, *CheckSpec*, *Finding*, *CheckResult*, *ReviewPlan*, *ReviewRun*,
*DocumentImport*, *ProblemDetail*. Changing a model means regenerating
the TypeScript contract (``python scripts/export_schemas.py``) and updating the tests.
"""

from bim_intelligence.schemas.ai import (
    BudgetStatus,
    EvidenceCitation,
    Explanation,
    ExplanationFallbackReason,
)
from bim_intelligence.schemas.canonical import canonical_json, compact_canonical_json, content_hash
from bim_intelligence.schemas.checks import CheckKind, CheckSpec, compute_check_id
from bim_intelligence.schemas.contracts import (
    CONTRACT_MODELS,
    build_contract_schema,
    contract_schema_json,
)
from bim_intelligence.schemas.documents import DocumentImport, DocumentKind
from bim_intelligence.schemas.elements import (
    ClassificationRef,
    ElementRecord,
    ElementRef,
    ModelSummary,
    PropertyValue,
)
from bim_intelligence.schemas.findings import (
    Finding,
    FindingMethod,
    Severity,
    compute_finding_id,
    findings_to_json,
    sort_findings,
)
from bim_intelligence.schemas.problems import ProblemDetail
from bim_intelligence.schemas.requirements import (
    Requirement,
    RequirementCandidate,
    RequirementCandidateBatch,
    RequirementCandidateConfirmation,
    RequirementExtractionRequest,
    RequirementOrigin,
    RequirementSource,
    RequirementStatus,
)
from bim_intelligence.schemas.runs import (
    TERMINAL_RUN_STATUSES,
    CheckResult,
    CheckStatus,
    InputManifest,
    PlannedCheck,
    PlanSource,
    ReviewPlan,
    ReviewRequest,
    ReviewRun,
    RunStatus,
)
from bim_intelligence.schemas.sessions import SESSION_ID_PATTERN, Session, SessionStatus

__all__ = [
    "CONTRACT_MODELS",
    "SESSION_ID_PATTERN",
    "TERMINAL_RUN_STATUSES",
    "BudgetStatus",
    "CheckKind",
    "CheckResult",
    "CheckSpec",
    "CheckStatus",
    "ClassificationRef",
    "DocumentImport",
    "DocumentKind",
    "ElementRecord",
    "ElementRef",
    "EvidenceCitation",
    "Explanation",
    "ExplanationFallbackReason",
    "Finding",
    "FindingMethod",
    "InputManifest",
    "ModelSummary",
    "PlanSource",
    "PlannedCheck",
    "ProblemDetail",
    "PropertyValue",
    "Requirement",
    "RequirementCandidate",
    "RequirementCandidateBatch",
    "RequirementCandidateConfirmation",
    "RequirementExtractionRequest",
    "RequirementOrigin",
    "RequirementSource",
    "RequirementStatus",
    "ReviewPlan",
    "ReviewRequest",
    "ReviewRun",
    "RunStatus",
    "Session",
    "SessionStatus",
    "Severity",
    "build_contract_schema",
    "canonical_json",
    "compact_canonical_json",
    "compute_check_id",
    "compute_finding_id",
    "content_hash",
    "contract_schema_json",
    "findings_to_json",
    "sort_findings",
]
