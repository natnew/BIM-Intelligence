"""Resolve an IfcOpenShell entity to the ``ElementRef`` the rest of the system uses (C-03).

The validator reports entities IfcTester hands back; findings must refer to them with exactly
the reference the Model Index serves, so the viewer, ``GET /elements/{globalId}`` and
``findings.json`` agree. Entities the index does not carry (an IDS applicability can match
non-product entities such as ``IfcProject``) get a reference built the same way the indexer
builds them.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import ifcopenshell
import ifcopenshell.util.element

from bim_intelligence.bim.errors import UnknownElementError
from bim_intelligence.bim.model_index import ModelIndex
from bim_intelligence.schemas import ElementRef
from bim_intelligence.schemas.elements import IFC_GUID_PATTERN

_GUID_RE = re.compile(IFC_GUID_PATTERN)

ElementRefResolver = Callable[[ifcopenshell.entity_instance], ElementRef]


def element_ref_resolver(index: ModelIndex | None) -> ElementRefResolver:
    """A resolver that prefers the index's own reference and falls back to the entity."""

    def resolve(entity: ifcopenshell.entity_instance) -> ElementRef:
        if index is not None:
            try:
                return index.by_express_id(entity.id()).ref
            except UnknownElementError:
                pass
        return element_ref_from_entity(entity)

    return resolve


def element_ref_from_entity(entity: ifcopenshell.entity_instance) -> ElementRef:
    """Build a reference directly from the entity, mirroring the indexer's rules."""
    raw = getattr(entity, "GlobalId", None)
    global_id = raw if isinstance(raw, str) and _GUID_RE.fullmatch(raw) else None
    name = getattr(entity, "Name", None)
    storey = None
    if not entity.is_a("IfcTypeObject"):
        container = ifcopenshell.util.element.get_container(entity, ifc_class="IfcBuildingStorey")
        storey_name = getattr(container, "Name", None) if container is not None else None
        storey = str(storey_name) if storey_name else None
    return ElementRef(
        global_id=global_id,
        express_id=entity.id(),
        ifc_type=entity.is_a(),
        name=str(name) if name else None,
        storey=storey,
    )
