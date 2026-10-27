"""Base classes shared by every contract model.

All domain models forbid unknown fields so that a payload with an unexpected key — a
model-supplied ``params`` on a planned check, an ``llm`` method, a stray timestamp — fails
loudly instead of being silently dropped. Serialisation schemas mark defaulted fields as
required because API responses always carry every field; the generated TypeScript therefore
has no spurious optionals (ADR-014).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """Mutable record whose shape is part of the backend/frontend contract."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        json_schema_serialization_defaults_required=True,
    )


class FrozenContractModel(ContractModel):
    """Immutable value object. Hashable when all fields are hashable."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_serialization_defaults_required=True,
    )
