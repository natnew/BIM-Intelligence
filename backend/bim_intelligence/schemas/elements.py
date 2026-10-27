"""Element references and the model summary (ARCHITECTURE §10.2, C-03).

``ElementRef`` is the only way any part of the system refers to an IFC element. The GlobalId is
the viewer-facing join key (ADR-007); ``express_id`` is always present and serves as a
diagnostic and as the fallback identity for entities without a GlobalId.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import Field, field_validator

from bim_intelligence.schemas.base import FrozenContractModel

IFC_GUID_PATTERN = r"^[0-9A-Za-z_$]{22}$"
IFC_CLASS_PATTERN = r"^Ifc[A-Za-z0-9]+$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"

_IFC_CLASS_RE = re.compile(IFC_CLASS_PATTERN)

GlobalId = Annotated[str, Field(pattern=IFC_GUID_PATTERN, description="22-character IFC GUID.")]
IfcClassName = Annotated[str, Field(pattern=IFC_CLASS_PATTERN, examples=["IfcWall"])]
Sha256Hex = Annotated[str, Field(pattern=SHA256_PATTERN, description="Lower-case SHA-256 hex.")]


class ElementRef(FrozenContractModel):
    """A reference to one entity in the uploaded model."""

    global_id: GlobalId | None = Field(
        description="IFC GlobalId; None for entities that are not IfcRoot subtypes."
    )
    express_id: int = Field(ge=1, description="STEP instance id (#n) within the stored file.")
    ifc_type: IfcClassName
    name: str | None = None
    storey: str | None = Field(default=None, description="Name of the containing storey.")

    @property
    def key(self) -> str:
        """Stable identity used for ordering and hashing: GlobalId, else ``#express_id``."""
        return self.global_id if self.global_id is not None else f"#{self.express_id}"


class ModelSummary(FrozenContractModel):
    """Headline facts about an uploaded model, produced once per upload."""

    ifc_schema: str = Field(examples=["IFC4"], description="Schema identifier read from the file.")
    model_hash: Sha256Hex
    project_name: str | None = None
    counts: dict[str, Annotated[int, Field(ge=0)]] = Field(
        description="Number of instances per IFC class, keyed by class name (e.g. IfcWall)."
    )
    storeys: list[ElementRef] = Field(description="Building storeys in file order.")

    @field_validator("counts")
    @classmethod
    def _keys_are_ifc_class_names(cls, counts: dict[str, int]) -> dict[str, int]:
        # Validated here rather than via propertyNames so the exported JSON Schema stays simple.
        invalid = [key for key in counts if not _IFC_CLASS_RE.match(key)]
        if invalid:
            raise ValueError(f"counts keys must be IFC class names, got {invalid!r}")
        return counts

    @property
    def element_count(self) -> int:
        return sum(self.counts.values())
