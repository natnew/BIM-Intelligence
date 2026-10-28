"""Build a :class:`ModelIndex` from an open IfcOpenShell file (FR-ING-02, ARCHITECTURE §8.1).

Indexed entities are every ``IfcProduct`` (which includes spatial elements) and every
``IfcTypeObject``. Values are read through ``ifcopenshell.util`` so that the index agrees with
IfcOpenShell by construction; the tests assert that equality. No geometry is evaluated
(ADR-007).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

import ifcopenshell
import ifcopenshell.util.classification
import ifcopenshell.util.element

from bim_intelligence.bim.model_index import ModelIndex
from bim_intelligence.schemas import (
    ClassificationRef,
    ElementRecord,
    ElementRef,
    ModelSummary,
    PropertyValue,
)
from bim_intelligence.schemas.elements import IFC_GUID_PATTERN

_GUID_RE = re.compile(IFC_GUID_PATTERN)
_INDEXED_ROOTS = ("IfcProduct", "IfcTypeObject")


def build_index(model: ifcopenshell.file, *, model_hash: str) -> ModelIndex:
    """Index ``model`` without modifying it. ``model_hash`` is the SHA-256 of the stored bytes."""
    entities = _indexable_entities(model)
    malformed: dict[int, str | None] = {}
    refs: dict[int, ElementRef] = {}
    for entity in entities:
        raw = getattr(entity, "GlobalId", None)
        global_id = raw if isinstance(raw, str) and _GUID_RE.fullmatch(raw) else None
        if global_id is None:
            malformed[entity.id()] = raw if raw is None or isinstance(raw, str) else str(raw)
        refs[entity.id()] = ElementRef(
            global_id=global_id,
            express_id=entity.id(),
            ifc_type=entity.is_a(),
            name=_optional_str(getattr(entity, "Name", None)),
            storey=_storey_name(entity),
        )

    records = [_record(entity, refs) for entity in entities]

    by_global_id: dict[str, list[int]] = {}
    for ref in refs.values():
        if ref.global_id is not None:
            by_global_id.setdefault(ref.global_id, []).append(ref.express_id)
    duplicates = {gid: ids for gid, ids in sorted(by_global_id.items()) if len(ids) > 1}

    summary = ModelSummary(
        ifc_schema=str(model.schema_identifier),
        model_hash=model_hash,
        project_name=_project_name(model),
        counts=dict(sorted(Counter(ref.ifc_type for ref in refs.values()).items())),
        storeys=[refs[s.id()] for s in _sorted(model.by_type("IfcBuildingStorey"))],
    )
    return ModelIndex(
        summary=summary,
        elements=records,
        duplicate_global_ids=duplicates,
        malformed_global_ids=malformed,
    )


def _indexable_entities(model: ifcopenshell.file) -> list[ifcopenshell.entity_instance]:
    seen: dict[int, ifcopenshell.entity_instance] = {}
    for root in _INDEXED_ROOTS:
        for entity in model.by_type(root):
            seen.setdefault(entity.id(), entity)
    return [seen[key] for key in sorted(seen)]


def _record(entity: ifcopenshell.entity_instance, refs: dict[int, ElementRef]) -> ElementRecord:
    is_type = bool(entity.is_a("IfcTypeObject"))
    type_entity = None if is_type else ifcopenshell.util.element.get_type(entity)
    container = None if is_type else ifcopenshell.util.element.get_container(entity)
    return ElementRecord(
        ref=refs[entity.id()],
        object_type=_optional_str(getattr(entity, "ObjectType", None)),
        predefined_type=_optional_str(ifcopenshell.util.element.get_predefined_type(entity)),
        type_ref=_ref_for(type_entity, refs),
        container=_ref_for(container, refs),
        psets=_psets_with_provenance(entity, type_entity),
        classifications=_classifications(entity),
    )


def _psets_with_provenance(
    entity: ifcopenshell.entity_instance, type_entity: ifcopenshell.entity_instance | None
) -> dict[str, dict[str, PropertyValue]]:
    """Reproduce ``get_psets(entity)``'s merge (type first, instance overrides) with flags."""
    merged: dict[str, dict[str, PropertyValue]] = {}
    if type_entity is not None:
        for pset, props in ifcopenshell.util.element.get_psets(
            type_entity, should_inherit=False
        ).items():
            merged[pset] = {
                name: PropertyValue(value=_json_value(value), inherited=True)
                for name, value in props.items()
                if name != "id"
            }
    for pset, props in ifcopenshell.util.element.get_psets(entity, should_inherit=False).items():
        target = merged.setdefault(pset, {})
        for name, value in props.items():
            if name != "id":
                target[name] = PropertyValue(value=_json_value(value), inherited=False)
    return merged


def _classifications(entity: ifcopenshell.entity_instance) -> list[ClassificationRef]:
    own = ifcopenshell.util.classification.get_references(entity, should_inherit=False)
    effective = ifcopenshell.util.classification.get_references(entity)
    refs = [
        ClassificationRef(
            system=_system_name(reference),
            # IFC4 names the code ``Identification``; IFC2X3 ``ItemReference``.
            identification=_optional_str(
                getattr(reference, "Identification", None)
                or getattr(reference, "ItemReference", None)
            ),
            name=_optional_str(getattr(reference, "Name", None)),
            inherited=reference not in own,
        )
        for reference in effective
    ]
    return sorted(refs, key=lambda r: (r.system or "", r.identification or "", r.name or ""))


def _system_name(reference: ifcopenshell.entity_instance) -> str | None:
    classification = ifcopenshell.util.classification.get_classification(reference)
    return _optional_str(getattr(classification, "Name", None)) if classification else None


def _storey_name(entity: ifcopenshell.entity_instance) -> str | None:
    if entity.is_a("IfcTypeObject"):
        return None
    storey = ifcopenshell.util.element.get_container(entity, ifc_class="IfcBuildingStorey")
    return _optional_str(getattr(storey, "Name", None)) if storey is not None else None


def _project_name(model: ifcopenshell.file) -> str | None:
    projects = _sorted(model.by_type("IfcProject"))
    return _optional_str(projects[0].Name) if projects else None


def _ref_for(
    entity: ifcopenshell.entity_instance | None, refs: dict[int, ElementRef]
) -> ElementRef | None:
    if entity is None:
        return None
    ref = refs.get(entity.id())
    if ref is None:  # pragma: no cover - containers and types are always indexed
        ref = ElementRef(
            global_id=None,
            express_id=entity.id(),
            ifc_type=entity.is_a(),
            name=_optional_str(getattr(entity, "Name", None)),
        )
    return ref


def _sorted(entities: Iterable[ifcopenshell.entity_instance]) -> list[ifcopenshell.entity_instance]:
    return sorted(entities, key=lambda e: e.id())


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _json_value(value: Any) -> Any:
    """Coerce an IfcOpenShell property value to JSON-compatible data."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, ifcopenshell.entity_instance):
        return f"#{value.id()}"
    return str(value)
