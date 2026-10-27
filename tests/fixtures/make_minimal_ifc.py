"""Generate the minimal IFC4 fixture and its IDS (BAKEOFF review §7.1, T-0).

Run from the repository root to (re)write ``tests/fixtures/minimal.ifc`` and ``minimal.ids``::

    python tests/fixtures/make_minimal_ifc.py

Output is byte-reproducible: GlobalIds are UUID5-derived, header timestamps are fixed and the
file is written with LF line endings on every platform. Any intentional change to the model
therefore changes the SHA-256 pinned in ``tests/unit/fixtures/test_minimal_fixture.py``.

Model: one project → site → building → storey ``L00`` containing three walls with extruded
geometry and distinct placements.

====== ========== ========== ==================== =====================================
Wall   IsExternal FireRating Classification        Expected outcome
====== ========== ========== ==================== =====================================
W-001  TRUE       REI 60     Ss_25_10_30           compliant
W-002  TRUE       —          Ss_25_10_30           fails spec 1 (FireRating missing)
W-003  FALSE      REI 30     —                     not applicable to spec 1; fails spec 2
====== ========== ========== ==================== =====================================
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.classification
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit
import ifcopenshell.guid
import ifcopenshell.ifcopenshell_wrapper as ifcopenshell_wrapper
import ifctester.ids
import numpy as np

FIXTURE_DIR = Path(__file__).resolve().parent
IFC_PATH = FIXTURE_DIR / "minimal.ifc"
IDS_PATH = FIXTURE_DIR / "minimal.ids"

GUID_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL, "https://github.com/natnew/BIM-Intelligence/fixtures/minimal"
)
FIXED_TIMESTAMP = "2026-10-27T00:00:00"
CLASSIFICATION_SYSTEM = "Uniclass 2015"

SPEC_FIRE_RATING = "External walls carry a fire rating"
SPEC_CLASSIFICATION = "Walls carry a classification reference"


@dataclass(frozen=True)
class WallSpec:
    name: str
    is_external: bool
    fire_rating: str | None
    classification: str | None
    # Placement origin in metres; walls run along +X.
    origin: tuple[float, float, float]
    length: float = 5.0
    height: float = 3.0
    thickness: float = 0.2


WALLS: tuple[WallSpec, ...] = (
    WallSpec("W-001", True, "REI 60", "Ss_25_10_30", origin=(0.0, 0.0, 0.0)),
    WallSpec("W-002", True, None, "Ss_25_10_30", origin=(0.0, 6.0, 0.0)),
    WallSpec("W-003", False, "REI 30", None, origin=(7.0, 0.0, 0.0)),
)

SPATIAL_NAMES = ("Minimal Project", "Site", "Building", "L00")


def deterministic_guid(label: str) -> str:
    """A valid IFC GlobalId derived only from ``label``."""
    return ifcopenshell.guid.compress(uuid.uuid5(GUID_NAMESPACE, label).hex)


GLOBAL_IDS: dict[str, str] = {
    name: deterministic_guid(name) for name in (*SPATIAL_NAMES, *(w.name for w in WALLS))
}


def build_minimal_ifc() -> ifcopenshell.file:
    file = ifcopenshell.api.project.create_file(version="IFC4")
    _fix_header(file)

    project = _create(file, "IfcProject", "Minimal Project")
    ifcopenshell.api.unit.assign_unit(file, length={"is_metric": True, "raw": "METERS"})
    model_context = ifcopenshell.api.context.add_context(file, context_type="Model")
    body_context = ifcopenshell.api.context.add_context(
        file,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )

    site = _create(file, "IfcSite", "Site")
    building = _create(file, "IfcBuilding", "Building")
    storey = _create(file, "IfcBuildingStorey", "L00")
    ifcopenshell.api.aggregate.assign_object(file, products=[site], relating_object=project)
    ifcopenshell.api.aggregate.assign_object(file, products=[building], relating_object=site)
    ifcopenshell.api.aggregate.assign_object(file, products=[storey], relating_object=building)
    for spatial in (site, building, storey):
        ifcopenshell.api.geometry.edit_object_placement(file, product=spatial, matrix=np.eye(4))

    classification = ifcopenshell.api.classification.add_classification(
        file, classification=CLASSIFICATION_SYSTEM
    )

    for spec in WALLS:
        wall = _create(file, "IfcWall", spec.name)
        ifcopenshell.api.spatial.assign_container(file, products=[wall], relating_structure=storey)

        placement = np.eye(4)
        placement[:3, 3] = spec.origin
        ifcopenshell.api.geometry.edit_object_placement(file, product=wall, matrix=placement)
        representation = ifcopenshell.api.geometry.add_wall_representation(
            file,
            context=body_context,
            length=spec.length,
            height=spec.height,
            thickness=spec.thickness,
        )
        ifcopenshell.api.geometry.assign_representation(
            file, product=wall, representation=representation
        )

        pset = ifcopenshell.api.pset.add_pset(file, product=wall, name="Pset_WallCommon")
        properties: dict[str, object] = {"IsExternal": spec.is_external}
        if spec.fire_rating is not None:
            properties["FireRating"] = spec.fire_rating
        ifcopenshell.api.pset.edit_pset(file, pset=pset, properties=properties)

        if spec.classification is not None:
            ifcopenshell.api.classification.add_reference(
                file,
                products=[wall],
                identification=spec.classification,
                name="Wall systems",
                classification=classification,
            )

    _pin_remaining_guids(file)
    _canonicalise_unordered_aggregates(file)
    _assert_guids_unique(file)
    return file


def build_minimal_ids() -> ifctester.ids.Ids:
    ids = ifctester.ids.Ids(
        title="BIM Intelligence minimal fixture",
        description=(
            "Two specifications exercising applicability, a property requirement "
            "and a classification requirement."
        ),
        author="fixtures@bim-intelligence.invalid",
        date="2026-10-27",
        version="1.0.0",
        purpose="Test fixture",
    )

    fire = ifctester.ids.Specification(
        name=SPEC_FIRE_RATING,
        ifcVersion=["IFC4"],
        minOccurs=1,
        maxOccurs="unbounded",
        description="Every external wall shall declare its fire rating.",
    )
    fire.applicability.append(ifctester.ids.Entity(name="IFCWALL"))
    fire.applicability.append(
        ifctester.ids.Property(
            propertySet="Pset_WallCommon",
            baseName="IsExternal",
            value="TRUE",
            dataType="IFCBOOLEAN",
        )
    )
    fire.requirements.append(
        ifctester.ids.Property(
            propertySet="Pset_WallCommon",
            baseName="FireRating",
            dataType="IFCLABEL",
            cardinality="required",
        )
    )

    classified = ifctester.ids.Specification(
        name=SPEC_CLASSIFICATION,
        ifcVersion=["IFC4"],
        minOccurs=1,
        maxOccurs="unbounded",
        description="Every wall shall carry a classification reference in the project system.",
    )
    classified.applicability.append(ifctester.ids.Entity(name="IFCWALL"))
    classified.requirements.append(
        ifctester.ids.Classification(system=CLASSIFICATION_SYSTEM, cardinality="required")
    )

    ids.specifications.extend([fire, classified])
    return ids


def ifc_bytes() -> bytes:
    """IFC-SPF bytes with LF line endings regardless of platform."""
    text: str = build_minimal_ifc().to_string()
    return text.replace("\r\n", "\n").encode("utf-8")


def ids_bytes() -> bytes:
    text: str = build_minimal_ids().to_string()
    return text.replace("\r\n", "\n").encode("utf-8")


def write_fixtures(directory: Path = FIXTURE_DIR) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    ifc_out = directory / IFC_PATH.name
    ids_out = directory / IDS_PATH.name
    ifc_out.write_bytes(ifc_bytes())
    ids_out.write_bytes(ids_bytes())
    return ifc_out, ids_out


def _fix_header(file: ifcopenshell.file) -> None:
    header = file.header
    header.file_description.description = ("ViewDefinition[ReferenceView]",)
    header.file_name.name = IFC_PATH.name
    header.file_name.time_stamp = FIXED_TIMESTAMP
    header.file_name.author = ("BIM Intelligence fixtures",)
    header.file_name.organization = ("natnew/BIM-Intelligence",)
    header.file_name.preprocessor_version = "tests/fixtures/make_minimal_ifc.py"
    header.file_name.originating_system = "BIM Intelligence"
    header.file_name.authorization = "none"


def _create(file: ifcopenshell.file, ifc_class: str, name: str) -> ifcopenshell.entity_instance:
    entity = ifcopenshell.api.root.create_entity(file, ifc_class=ifc_class, name=name)
    entity.GlobalId = GLOBAL_IDS[name]
    return entity


def _pin_remaining_guids(file: ifcopenshell.file) -> None:
    """Relationships and property sets receive random GlobalIds from the API; fix them.

    Express ids are deterministic (creation order), so ``<class>#<id>`` is a stable label.
    """
    named = set(GLOBAL_IDS.values())
    for entity in file.by_type("IfcRoot"):
        if entity.GlobalId not in named:
            entity.GlobalId = deterministic_guid(f"{entity.is_a()}#{entity.id()}")


def _canonicalise_unordered_aggregates(file: ifcopenshell.file) -> None:
    """Sort every EXPRESS SET/BAG of entity references by express id.

    The API builds e.g. ``RelatedElements`` and ``Units`` from Python sets, whose iteration order
    varies between processes. SET order carries no meaning in IFC, so sorting is semantically
    neutral and makes the serialised file reproducible. LIST/ARRAY aggregates are untouched.
    """
    # The SWIG schema wrapper has no stubs for declaration introspection.
    schema: Any = ifcopenshell_wrapper.schema_by_name(file.schema_identifier)
    unordered = {
        ifcopenshell_wrapper.aggregation_type.set_type,
        ifcopenshell_wrapper.aggregation_type.bag_type,
    }
    for entity in file:
        declaration = schema.declaration_by_name(entity.is_a())
        derived: tuple[bool, ...] = declaration.derived()
        for index, attribute in enumerate(declaration.all_attributes()):
            attribute_type = attribute.type_of_attribute()
            if derived[index] or not isinstance(
                attribute_type, ifcopenshell_wrapper.aggregation_type
            ):
                continue
            if attribute_type.type_of_aggregation() not in unordered:
                continue
            value = entity[index]
            if (
                isinstance(value, tuple)
                and value
                and all(isinstance(v, ifcopenshell.entity_instance) for v in value)
            ):
                entity[index] = tuple(sorted(value, key=lambda v: v.id()))


def _assert_guids_unique(file: ifcopenshell.file) -> None:
    guids = [entity.GlobalId for entity in file.by_type("IfcRoot")]
    if len(guids) != len(set(guids)):
        raise RuntimeError(
            "fixture GlobalIds collide; change the labels passed to deterministic_guid"
        )


def main() -> int:
    ifc_out, ids_out = write_fixtures()
    print(f"wrote {ifc_out.relative_to(Path.cwd())} ({ifc_out.stat().st_size} bytes)")
    print(f"wrote {ids_out.relative_to(Path.cwd())} ({ids_out.stat().st_size} bytes)")
    for name, guid in GLOBAL_IDS.items():
        print(f"{name:16} {guid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
