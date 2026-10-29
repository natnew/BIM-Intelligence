"""Deterministic validation: IDS compilation, execution and finding normalisation (ADR-001).

This package and ``bim/`` are the only ones that import ``ifcopenshell`` / ``ifctester``
(AGENTS.md §3). ``requirements/`` imports the compiler; ``orchestration/`` imports the runner.
"""

from bim_intelligence.validation.errors import CheckSpecIntegrityError, IdsError, InvalidIdsError
from bim_intelligence.validation.ids_compiler import (
    IDS_NAMESPACE,
    IDS_VERSION,
    CompiledIds,
    CompiledSpecification,
    canonical_specification_xml,
    compile_ids,
    hydrate_specification,
    ids_schema,
)
from bim_intelligence.validation.ids_runner import CheckOutcome, ValidationTarget, run_ids_check
from bim_intelligence.validation.native_rules import (
    CLASSIFICATION_CONSISTENCY_RULE_ID,
    CLASSIFICATION_CONSISTENCY_RULE_VERSION,
    CLASSIFICATION_CONSISTENCY_STATEMENT,
    CLASSIFICATION_CONSISTENCY_TITLE,
    classification_consistency_check,
    run_native_check,
)
from bim_intelligence.validation.normaliser import (
    PROHIBITED_ENTITY_CATEGORY,
    facet_category,
    normalise_specification,
)

__all__ = [
    "CLASSIFICATION_CONSISTENCY_RULE_ID",
    "CLASSIFICATION_CONSISTENCY_RULE_VERSION",
    "CLASSIFICATION_CONSISTENCY_STATEMENT",
    "CLASSIFICATION_CONSISTENCY_TITLE",
    "IDS_NAMESPACE",
    "IDS_VERSION",
    "PROHIBITED_ENTITY_CATEGORY",
    "CheckOutcome",
    "CheckSpecIntegrityError",
    "CompiledIds",
    "CompiledSpecification",
    "IdsError",
    "InvalidIdsError",
    "ValidationTarget",
    "canonical_specification_xml",
    "classification_consistency_check",
    "compile_ids",
    "facet_category",
    "hydrate_specification",
    "ids_schema",
    "normalise_specification",
    "run_ids_check",
    "run_native_check",
]
