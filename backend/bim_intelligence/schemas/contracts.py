"""The JSON Schema bundle exported to the frontend (ADR-014, W-17).

``build_contract_schema()`` is the single source of truth for ``frontend/src/api/generated/``.
It uses serialisation mode so derived fields such as ``Finding.id`` appear as required: the
frontend only ever *reads* these shapes from API responses.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema, models_json_schema
from pydantic_core import CoreSchema

from bim_intelligence.schemas.canonical import canonical_json
from bim_intelligence.schemas.checks import CheckSpec
from bim_intelligence.schemas.elements import ElementRef, ModelSummary
from bim_intelligence.schemas.findings import Finding
from bim_intelligence.schemas.problems import ProblemDetail
from bim_intelligence.schemas.requirements import Requirement, RequirementSource
from bim_intelligence.schemas.runs import (
    CheckResult,
    InputManifest,
    PlannedCheck,
    ReviewPlan,
    ReviewRun,
)

CONTRACT_MODELS: tuple[type[BaseModel], ...] = (
    ElementRef,
    ModelSummary,
    CheckSpec,
    RequirementSource,
    Requirement,
    Finding,
    CheckResult,
    PlannedCheck,
    ReviewPlan,
    InputManifest,
    ReviewRun,
    ProblemDetail,
)

SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
BUNDLE_TITLE = "BimIntelligenceContracts"


class _ModelTitlesOnly(GenerateJsonSchema):
    """Omit per-field ``title``s.

    json-schema-to-typescript turns every titled property into a top-level alias
    (``CheckId``, ``CheckId1``, …); without them each field is typed inline and only the
    models become named types.
    """

    def field_title_should_be_set(self, schema: CoreSchema) -> bool:
        return False


def build_contract_schema() -> dict[str, Any]:
    """One JSON Schema document whose ``$defs`` hold every contract model.

    The root object exposes each model under a camel-cased property so that generators which
    require a typed root (json-schema-to-typescript) emit one named type per model.
    """
    _, bundle = models_json_schema(
        [(model, "serialization") for model in CONTRACT_MODELS],
        ref_template="#/$defs/{model}",
        schema_generator=_ModelTitlesOnly,
    )
    defs: dict[str, Any] = bundle["$defs"]
    return {
        "$schema": SCHEMA_DIALECT,
        "$id": "https://github.com/natnew/BIM-Intelligence/schemas/contracts.json",
        "title": BUNDLE_TITLE,
        "description": (
            "Generated from backend/bim_intelligence/schemas by scripts/export_schemas.py. "
            "Do not edit by hand."
        ),
        "type": "object",
        "additionalProperties": False,
        "properties": {
            _camel(model.__name__): {"$ref": f"#/$defs/{model.__name__}"}
            for model in CONTRACT_MODELS
        },
        "$defs": {name: defs[name] for name in sorted(defs)},
    }


def contract_schema_json() -> str:
    return canonical_json(build_contract_schema())


def _camel(name: str) -> str:
    return name[0].lower() + name[1:]
