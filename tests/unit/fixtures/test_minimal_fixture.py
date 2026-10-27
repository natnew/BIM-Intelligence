"""Integrity of the committed minimal IFC/IDS fixture (BAKEOFF review §7.1, T-0).

The fixture is the first input every later slice step consumes, so these tests pin its bytes,
its GlobalIds, its semantics (which walls fail which specification) and its geometry.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.classification
import ifcopenshell.util.element
import ifcopenshell.util.representation
import ifcopenshell.validate
import ifctester.ids
import pytest

from fixtures.make_minimal_ifc import (
    GLOBAL_IDS,
    IDS_PATH,
    IFC_PATH,
    SPEC_CLASSIFICATION,
    SPEC_FIRE_RATING,
    WALLS,
    ids_bytes,
    ifc_bytes,
    write_fixtures,
)

# Pinned when the fixture was first generated; a change here is a deliberate fixture revision.
EXPECTED_IFC_SHA256 = "f2bd00074c54866d95c5c344a1c604e01cdb8ea394b9b20937952b7b38c74348"
EXPECTED_IDS_SHA256 = "e602233db1e9aa8e77b2a4f90371db42df9879ee2f6331251f7aab84f2f1ce74"
EXPECTED_GLOBAL_IDS = {
    "L00": "2yfsJW2FHUWvdouGfT1ctg",
    "W-001": "21KH8X9wHPWw7JLiY2NtSZ",
    "W-002": "0QWMtUzsnUUONCUGc8Sqsa",
    "W-003": "2qvnbd6oPPKR1ac5HegGTJ",
}


@pytest.fixture(scope="module")
def model() -> ifcopenshell.file:
    return ifcopenshell.open(str(IFC_PATH))


def _walls_by_name(model: ifcopenshell.file) -> dict[str, ifcopenshell.entity_instance]:
    return {wall.Name: wall for wall in model.by_type("IfcWall")}


def test_committed_files_exist_and_match_pinned_hashes() -> None:
    assert IFC_PATH.exists() and IDS_PATH.exists(), "run: python tests/fixtures/make_minimal_ifc.py"
    assert hashlib.sha256(IFC_PATH.read_bytes()).hexdigest() == EXPECTED_IFC_SHA256
    assert hashlib.sha256(IDS_PATH.read_bytes()).hexdigest() == EXPECTED_IDS_SHA256


def test_generator_reproduces_committed_bytes_exactly(tmp_path: Path) -> None:
    ifc_out, ids_out = write_fixtures(tmp_path)
    assert ifc_out.read_bytes() == IFC_PATH.read_bytes()
    assert ids_out.read_bytes() == IDS_PATH.read_bytes()


def test_generator_is_deterministic_across_invocations() -> None:
    assert ifc_bytes() == ifc_bytes()
    assert ids_bytes() == ids_bytes()
    assert b"\r\n" not in ifc_bytes(), "fixture must use LF so the hash is identical on every OS"


def test_global_ids_are_pinned(model: ifcopenshell.file) -> None:
    for name, expected in EXPECTED_GLOBAL_IDS.items():
        assert GLOBAL_IDS[name] == expected, name
    walls = _walls_by_name(model)
    for name, expected in EXPECTED_GLOBAL_IDS.items():
        entity = walls[name] if name.startswith("W-") else model.by_type("IfcBuildingStorey")[0]
        assert entity.GlobalId == expected, name
    all_guids = [entity.GlobalId for entity in model.by_type("IfcRoot")]
    assert len(all_guids) == len(set(all_guids)), "GlobalIds must be unique"


def test_structure_is_ifc4_with_one_storey_and_three_contained_walls(
    model: ifcopenshell.file,
) -> None:
    assert model.schema == "IFC4"
    storeys = model.by_type("IfcBuildingStorey")
    assert [storey.Name for storey in storeys] == ["L00"]
    walls = _walls_by_name(model)
    assert sorted(walls) == [wall.name for wall in WALLS] == ["W-001", "W-002", "W-003"]
    for wall in walls.values():
        assert ifcopenshell.util.element.get_container(wall) == storeys[0]
    assert len(model.by_type("IfcProject")) == 1


def test_property_sets_encode_the_two_expected_defects(model: ifcopenshell.file) -> None:
    walls = _walls_by_name(model)
    common = {
        name: ifcopenshell.util.element.get_pset(wall, "Pset_WallCommon")
        for name, wall in walls.items()
    }
    assert common["W-001"]["IsExternal"] is True
    assert common["W-001"]["FireRating"] == "REI 60"
    assert common["W-002"]["IsExternal"] is True
    assert "FireRating" not in common["W-002"]
    assert common["W-003"]["IsExternal"] is False
    assert common["W-003"]["FireRating"] == "REI 30"


def test_classification_is_present_on_external_walls_only(model: ifcopenshell.file) -> None:
    walls = _walls_by_name(model)
    references = {
        name: ifcopenshell.util.classification.get_references(wall) for name, wall in walls.items()
    }
    assert {ref.Identification for ref in references["W-001"]} == {WALLS[0].classification}
    assert {ref.Identification for ref in references["W-002"]} == {WALLS[1].classification}
    assert len(references["W-003"]) == 0


def test_ids_is_valid_and_yields_exactly_the_two_expected_failures(
    model: ifcopenshell.file,
) -> None:
    ids = ifctester.ids.open(str(IDS_PATH), validate=True)
    assert [spec.name for spec in ids.specifications] == [SPEC_FIRE_RATING, SPEC_CLASSIFICATION]
    ids.validate(model)
    fire, classification = ids.specifications

    assert {e.Name for e in fire.applicable_entities} == {"W-001", "W-002"}
    assert {e.Name for e in fire.failed_entities} == {"W-002"}
    assert fire.status is False

    assert {e.Name for e in classification.applicable_entities} == {"W-001", "W-002", "W-003"}
    assert {e.Name for e in classification.failed_entities} == {"W-003"}
    assert classification.status is False

    # ifctester 0.9.0 records each facet failure as {"element": entity, "reason": str} (Q-03).
    failures = [
        (spec.name, failure["element"].Name, failure["reason"])
        for spec in ids.specifications
        for requirement in spec.requirements
        for failure in requirement.failures
    ]
    assert sorted(failures) == [
        (SPEC_FIRE_RATING, "W-002", "The property set does not contain the required property"),
        (SPEC_CLASSIFICATION, "W-003", "The entity has no classification"),
    ]


class _CollectingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_fixture_passes_ifcopenshell_schema_validation(model: ifcopenshell.file) -> None:
    logger = logging.getLogger("fixture-validate")
    handler = _CollectingHandler()
    logger.addHandler(handler)
    try:
        ifcopenshell.validate.validate(model, logger)
    finally:
        logger.removeHandler(handler)
    assert [r.getMessage() for r in handler.records if r.levelno >= logging.ERROR] == []


def test_every_wall_has_a_placement_and_an_extruded_body(model: ifcopenshell.file) -> None:
    for wall in model.by_type("IfcWall"):
        assert wall.ObjectPlacement is not None and wall.ObjectPlacement.is_a("IfcLocalPlacement")
        body = ifcopenshell.util.representation.get_representation(
            wall, "Model", "Body", "MODEL_VIEW"
        )
        assert body is not None, wall.Name
        assert body.RepresentationType == "SweptSolid"
        assert all(item.is_a("IfcExtrudedAreaSolid") for item in body.Items)


def test_wall_geometry_tessellates_to_distinct_non_degenerate_meshes(
    model: ifcopenshell.file,
) -> None:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    origins: list[tuple[float, float, float]] = []
    for wall in sorted(model.by_type("IfcWall"), key=lambda w: w.Name):
        # create_shape returns a SWIG union; the triangulation branch is what settings select.
        shape: Any = ifcopenshell.geom.create_shape(settings, wall)
        verts: list[float] = list(shape.geometry.verts)
        faces: list[int] = list(shape.geometry.faces)
        assert len(verts) >= 8 * 3 and len(faces) >= 12 * 3, wall.Name
        xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
        extent = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
        assert all(axis > 0.1 for axis in extent), (wall.Name, extent)
        origins.append((min(xs), min(ys), min(zs)))
    assert len(set(origins)) == 3, "walls must not be stacked on the same placement"
