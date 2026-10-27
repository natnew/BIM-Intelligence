"""CheckSpec: the immutable, content-addressed statement of what a check asserts (C-02).

A review plan may select *which* confirmed checks run but can never alter *what* a check
asserts: ``run_ids_validation`` and ``run_native_rule`` take a ``CheckSpec`` resolved
server-side from its id, never model-supplied parameters.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, JsonValue, model_validator

from bim_intelligence.schemas.base import FrozenContractModel
from bim_intelligence.schemas.canonical import compact_canonical_json, content_hash

CheckKind = Literal["ids", "native"]


class CheckSpec(FrozenContractModel):
    """One executable check, compiled from exactly one requirement."""

    id: str = Field(
        default="",
        description=(
            "Content hash of kind, rule_id, rule_version and payload. Derived automatically "
            "when omitted; rejected when supplied and inconsistent."
        ),
    )
    kind: CheckKind
    rule_id: str = Field(
        min_length=1,
        examples=["ids:External walls carry a fire rating", "naming.pattern"],
        description="IDS specification reference (``ids:<name>``) or registered native rule id.",
    )
    rule_version: str = Field(
        min_length=1,
        description="IDS: hash of the specification XML. Native: the rule's semantic version.",
    )
    ids_specification: str | None = Field(
        default=None, description="Serialised IDS 1.0 <specification> element for ids checks."
    )
    params: dict[str, JsonValue] = Field(
        default_factory=dict, description="Native rule parameters; must be empty for ids checks."
    )

    @model_validator(mode="after")
    def _enforce_kind_payload(self) -> CheckSpec:
        if self.kind == "ids":
            if self.ids_specification is None:
                raise ValueError("ids checks require ids_specification")
            if self.params:
                raise ValueError(
                    "ids checks must not carry params; the specification is the payload"
                )
        elif self.ids_specification is not None:
            raise ValueError("native checks must not carry ids_specification")
        return self

    @model_validator(mode="after")
    def _derive_or_verify_id(self) -> CheckSpec:
        expected = compute_check_id(
            kind=self.kind,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            ids_specification=self.ids_specification,
            params=self.params,
        )
        if self.id == "":
            # Frozen model: bypass the immutability guard once, during validation only.
            object.__setattr__(self, "id", expected)
        elif self.id != expected:
            raise ValueError(
                f"id {self.id!r} is not the content-addressed id {expected!r} of this check"
            )
        return self


def compute_check_id(
    *,
    kind: CheckKind,
    rule_id: str,
    rule_version: str,
    ids_specification: str | None,
    params: dict[str, JsonValue],
) -> str:
    payload = ids_specification if kind == "ids" else compact_canonical_json(params)
    return content_hash(kind, rule_id, rule_version, payload or "")
