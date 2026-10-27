"""Finding: a deterministic defect record (ADR-001, FR-VAL-07, C-03).

Only IfcTester or a registered native rule may create a Finding; ``method`` has no ``llm``
member. Identity is content-addressed and there is no timestamp or run reference, so two runs
over the same inputs serialise to byte-identical ``findings.json`` (NFR-01).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import Field, field_validator, model_validator

from bim_intelligence.schemas.base import FrozenContractModel
from bim_intelligence.schemas.canonical import canonical_json, content_hash
from bim_intelligence.schemas.elements import ElementRef

FindingMethod = Literal["ids", "native"]
Severity = Literal["error", "warning", "info"]

CATEGORY_PATTERN = r"^[a-z][a-z0-9_]*$"


class Finding(FrozenContractModel):
    """One verified defect affecting one or more elements."""

    id: str = Field(
        default="",
        description=(
            "sha1(check_id | rule_version | facet_index | sorted element keys)[:16]. Derived "
            "automatically when omitted; rejected when supplied and inconsistent."
        ),
    )
    check_id: str = Field(min_length=1, description="Id of the CheckSpec that produced it.")
    requirement_id: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    rule_version: str = Field(min_length=1)
    facet_index: int = Field(
        ge=0, description="Index of the failing requirement facet within the check; 0 for native."
    )
    severity: Severity
    category: str = Field(
        pattern=CATEGORY_PATTERN,
        examples=["property_missing", "classification_missing", "prohibited_entity"],
    )
    elements: list[ElementRef] = Field(
        min_length=1, description="Affected elements, canonical order."
    )
    observed: str = Field(description="What the deterministic engine found.")
    expected: str = Field(description="What the requirement demanded.")
    method: FindingMethod

    @field_validator("elements")
    @classmethod
    def _canonical_element_order(cls, elements: list[ElementRef]) -> list[ElementRef]:
        return sorted(elements, key=lambda element: element.key)

    @model_validator(mode="after")
    def _derive_or_verify_id(self) -> Finding:
        expected = compute_finding_id(
            check_id=self.check_id,
            rule_version=self.rule_version,
            facet_index=self.facet_index,
            element_keys=[element.key for element in self.elements],
        )
        if self.id == "":
            # Frozen model: bypass the immutability guard once, during validation only.
            object.__setattr__(self, "id", expected)
        elif self.id != expected:
            raise ValueError(
                f"id {self.id!r} is not the content-addressed id {expected!r} of this finding"
            )
        return self

    @property
    def sort_key(self) -> tuple[str, int, str, str]:
        return (self.check_id, self.facet_index, self.elements[0].key, self.id)


def compute_finding_id(
    *, check_id: str, rule_version: str, facet_index: int, element_keys: Iterable[str]
) -> str:
    return content_hash(check_id, rule_version, str(facet_index), *sorted(element_keys))


def sort_findings(findings: Iterable[Finding]) -> list[Finding]:
    """Canonical order: ``(check_id, facet_index, first element key, id)``."""
    return sorted(findings, key=lambda finding: finding.sort_key)


def findings_to_json(findings: Iterable[Finding]) -> str:
    """The on-disk ``findings.json`` form: canonical order, sorted keys, trailing newline."""
    return canonical_json([finding.model_dump(mode="json") for finding in sort_findings(findings)])
