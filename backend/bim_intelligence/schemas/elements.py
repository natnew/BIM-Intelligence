"""Element references, element records and the model summary (ARCHITECTURE §10.2, C-03).

``ElementRef`` is the only way any part of the system refers to an IFC element. The GlobalId is
the viewer-facing join key (ADR-007); ``express_id`` is always present and serves as a
diagnostic and as the fallback identity for entities without a GlobalId. ``ElementRecord`` is
the denormalised Model Index entry served by ``GET /elements/{globalId}`` (FR-ING-04).
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import Field, JsonValue, field_validator

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


class PropertyValue(FrozenContractModel):
    """One property or quantity value with its provenance (C-03).

    ``value`` is the value as IfcOpenShell reads it: a scalar, a list for enumerations, or an
    object for bounded, table and complex properties. It carries no field description because
    a ``description`` beside ``$ref`` makes json-schema-to-typescript emit an object type.
    """

    value: JsonValue
    inherited: bool = Field(
        description="True when the value comes from the element's type object rather than "
        "being defined on the element itself."
    )


class ClassificationRef(FrozenContractModel):
    """A classification reference attached to an element, directly or through its type."""

    system: str | None = Field(description="Name of the IfcClassification, when resolvable.")
    identification: str | None = Field(
        description="Reference code (IFC4 Identification / IFC2X3 ItemReference)."
    )
    name: str | None = None
    inherited: bool = Field(description="True when inherited from the element's type object.")


class ElementRecord(FrozenContractModel):
    """Denormalised Model Index entry for one product, type object or spatial element."""

    ref: ElementRef
    object_type: str | None = Field(default=None, description="IfcObject.ObjectType attribute.")
    predefined_type: str | None = Field(
        default=None,
        description="Resolved PredefinedType (instance, then type, USERDEFINED→"
        "ObjectType/ElementType).",
    )
    type_ref: ElementRef | None = Field(
        default=None, description="The IfcTypeObject this occurrence is typed by, if any."
    )
    container: ElementRef | None = Field(
        default=None, description="Direct or aggregate-inherited spatial container, if any."
    )
    psets: dict[str, dict[str, PropertyValue]] = Field(
        description="Property and quantity sets keyed by set name, then property name."
    )
    classifications: list[ClassificationRef] = Field(
        description="Classification references in (system, identification, name) order."
    )

    def plain_psets(self) -> dict[str, dict[str, JsonValue]]:
        """Values only, in the shape ``ifcopenshell.util.element.get_psets`` returns minus ids."""
        return {
            pset: {name: prop.value for name, prop in props.items()}
            for pset, props in self.psets.items()
        }


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
