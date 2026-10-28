"""ElementRecord: the element view served by ``GET /elements/{globalId}`` (FR-ING-04, C-03)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bim_intelligence.schemas import ClassificationRef, ElementRecord, ElementRef, PropertyValue

WALL = ElementRef(
    global_id="21KH8X9wHPWw7JLiY2NtSZ",
    express_id=50,
    ifc_type="IfcWall",
    name="W-001",
    storey="L00",
)
STOREY = ElementRef(
    global_id="2yfsJW2FHUWvdouGfT1ctg", express_id=20, ifc_type="IfcBuildingStorey", name="L00"
)
WALL_TYPE = ElementRef(global_id="0Rl8DF7rH3Z8m0CjaIvG4l", express_id=9, ifc_type="IfcWallType")


def _record(**overrides: object) -> ElementRecord:
    fields: dict[str, object] = {
        "ref": WALL,
        "object_type": None,
        "predefined_type": "SOLIDWALL",
        "type_ref": WALL_TYPE,
        "container": STOREY,
        "psets": {
            "Pset_WallCommon": {
                "IsExternal": PropertyValue(value=True, inherited=False),
                "FireRating": PropertyValue(value="REI 60", inherited=True),
            }
        },
        "classifications": [
            ClassificationRef(
                system="Uniclass 2015",
                identification="Ss_25_10_30",
                name="Wall systems",
                inherited=False,
            )
        ],
    }
    fields.update(overrides)
    return ElementRecord(**fields)


def test_record_carries_identity_provenance_and_relationships() -> None:
    record = _record()
    assert record.ref.key == "21KH8X9wHPWw7JLiY2NtSZ"
    assert record.psets["Pset_WallCommon"]["FireRating"].inherited is True
    assert record.psets["Pset_WallCommon"]["IsExternal"].inherited is False
    assert record.container is not None and record.container.ifc_type == "IfcBuildingStorey"
    assert record.type_ref is not None and record.type_ref.ifc_type == "IfcWallType"


def test_plain_psets_projects_values_without_provenance() -> None:
    assert _record().plain_psets() == {
        "Pset_WallCommon": {"IsExternal": True, "FireRating": "REI 60"}
    }


def test_property_values_are_json_only() -> None:
    PropertyValue(value=None, inherited=False)
    PropertyValue(value=[1, 2.5, "x"], inherited=False)
    PropertyValue(value={"LowerBoundValue": 1, "UpperBoundValue": 2}, inherited=False)
    with pytest.raises(ValidationError):
        PropertyValue(value=object(), inherited=False)


def test_relationships_are_optional_but_provenance_is_not() -> None:
    record = _record(type_ref=None, container=None, psets={}, classifications=[])
    assert record.type_ref is None and record.container is None
    with pytest.raises(ValidationError):
        PropertyValue(value=1)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        ClassificationRef(system="Uniclass 2015", identification="Ss_25", name=None)  # type: ignore[call-arg]


def test_record_is_closed_to_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _record(geometry={"bbox": [0, 0, 0]})
