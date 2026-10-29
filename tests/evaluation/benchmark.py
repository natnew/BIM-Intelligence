"""Reproducible IFC4 benchmark inputs and independent defect ground truth."""

from __future__ import annotations

import hashlib
import json
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
import ifcopenshell.api.type
import ifcopenshell.api.unit
import ifcopenshell.guid
import ifctester.ids
import numpy as np
from ifctester.facet import Restriction

from bim_intelligence.validation import (
    CLASSIFICATION_CONSISTENCY_RULE_ID,
    CLASSIFICATION_CONSISTENCY_RULE_VERSION,
    classification_consistency_check,
    compile_ids,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "datasets" / "synthetic" / "generated"
MANIFEST_VERSION = "1.0.0"
CLASSIFICATION_SYSTEM = "Uniclass 2015"
WRONG_CLASSIFICATION_SYSTEM = "Benchmark test system"
FIRE_RATING_PATTERN = "REI [0-9]{2}"
WALL_NAME_PATTERN = "W-[0-9]{3}(-EXT)?"
DOOR_NAME_PATTERN = "D-[0-9]{3}"
STOREY_NAME_PATTERN = "L[0-9]{2}"

_GUID_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL, "https://github.com/natnew/BIM-Intelligence/datasets/synthetic/v1"
)
_FIXED_TIMESTAMP = "2026-10-29T00:00:00"
_MATCHING_CONTRACT = "exact rule_id and check_id and exact sorted GlobalId set; one-to-one"
_CHECK_FAMILIES: dict[str, str] = {
    "IDS:wall_fire_rating": "property.required",
    "IDS:door_fire_rating": "property.required",
    "IDS:space_reference": "property.required",
    "IDS:wall_name": "naming.pattern",
    "IDS:door_name": "naming.pattern",
    "IDS:storey_name": "naming.pattern",
    "IDS:window_classification": "classification.*",
    "IDS:wall_classification": "classification.*",
    "IDS:external_wall_applicability": "applicability.control",
    "IDS:column_non_applicability": "applicability.control",
}


@dataclass(frozen=True)
class BenchmarkArtifacts:
    clean_ifc: Path
    defective_ifc: Path
    ids: Path
    manifest: Path
    ground_truth: Path
    bep: Path
    objectives: Path


def deterministic_guid(label: str) -> str:
    """Return a stable, valid IFC GlobalId for a human-readable element label."""
    return ifcopenshell.guid.compress(uuid.uuid5(_GUID_NAMESPACE, label).hex)


def build_benchmark_ids() -> ifctester.ids.Ids:
    ids = ifctester.ids.Ids(
        title="BIM Intelligence synthetic architectural benchmark",
        description="Synthetic IFC4 requirements for deterministic evaluation.",
        author="fixtures@bim-intelligence.invalid",
        date="2026-10-29",
        version=MANIFEST_VERSION,
        purpose="T-6 deterministic benchmark",
    )
    specs = (
        _property_spec(
            "IDS:wall_fire_rating",
            "Walls have valid fire ratings",
            "IFCWALL",
            "Pset_WallCommon",
            "FireRating",
            FIRE_RATING_PATTERN,
        ),
        _property_spec(
            "IDS:door_fire_rating",
            "Doors have valid fire ratings",
            "IFCDOOR",
            "Pset_DoorCommon",
            "FireRating",
            FIRE_RATING_PATTERN,
        ),
        _property_spec(
            "IDS:space_reference",
            "Spaces declare a reference",
            "IFCSPACE",
            "Pset_SpaceCommon",
            "Reference",
        ),
        _attribute_spec(
            "IDS:wall_name", "Walls follow the naming pattern", "IFCWALL", WALL_NAME_PATTERN
        ),
        _attribute_spec(
            "IDS:door_name", "Doors follow the naming pattern", "IFCDOOR", DOOR_NAME_PATTERN
        ),
        _attribute_spec(
            "IDS:storey_name",
            "Storeys follow the naming pattern",
            "IFCBUILDINGSTOREY",
            STOREY_NAME_PATTERN,
        ),
        _classification_spec(
            "IDS:window_classification", "Windows use project classification", "IFCWINDOW"
        ),
        _classification_spec(
            "IDS:wall_classification", "Walls use project classification", "IFCWALL"
        ),
        _external_wall_applicability_spec(),
        _property_spec(
            "IDS:column_non_applicability",
            "Column requirement applicability control",
            "IFCCOLUMN",
            "Pset_ColumnCommon",
            "Reference",
        ),
    )
    ids.specifications.extend(specs)
    return ids


def generate_benchmark(output_dir: Path = DEFAULT_OUTPUT_DIR) -> BenchmarkArtifacts:
    """Write all deterministic benchmark artefacts beneath ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ids_bytes = _lf_bytes(build_benchmark_ids().to_string())
    compiled = compile_ids(ids_bytes)
    checks_by_id = {spec.name: spec.check for spec in compiled.specifications}

    clean_model = _build_model()
    _canonicalise_aggregates(clean_model)
    clean_bytes = _ifc_bytes(clean_model)

    defective_model = ifcopenshell.file.from_string(clean_bytes.decode("utf-8"))
    existing_guids = {root.id(): root.GlobalId for root in defective_model.by_type("IfcRoot")}
    injections = _inject_defects(defective_model, checks_by_id)
    _pin_new_root_guids(defective_model, existing_guids)
    _canonicalise_aggregates(defective_model)
    defective_bytes = _ifc_bytes(defective_model)
    _verify_clean_and_injected_facts(clean_bytes, defective_bytes, injections)

    clean_path = output_dir / "benchmark-clean.ifc"
    defective_path = output_dir / "benchmark-defective.ifc"
    ids_path = output_dir / "benchmark.ids"
    manifest_path = output_dir / "defect-injections.v1.json"
    ground_truth_path = output_dir / "ground_truth.json"
    bep_path = output_dir / "benchmark_bep.md"
    objectives_path = output_dir / "benchmark_objectives.json"

    _write_bytes(clean_path, clean_bytes)
    _write_bytes(defective_path, defective_bytes)
    _write_bytes(ids_path, ids_bytes)
    _write_json(manifest_path, _manifest_payload(injections, checks_by_id))
    _write_json(
        ground_truth_path,
        _ground_truth_payload(injections, checks_by_id, defective_bytes),
    )
    _write_text(bep_path, _benchmark_bep())
    _write_json(objectives_path, _benchmark_objectives())

    return BenchmarkArtifacts(
        clean_ifc=clean_path,
        defective_ifc=defective_path,
        ids=ids_path,
        manifest=manifest_path,
        ground_truth=ground_truth_path,
        bep=bep_path,
        objectives=objectives_path,
    )


def validate_ground_truth(artifacts: BenchmarkArtifacts) -> None:
    """Reject altered labels, missing targets or IFC facts inconsistent with the injection log."""
    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    truth = json.loads(artifacts.ground_truth.read_text(encoding="utf-8"))
    manifest_rows = {item["defect_id"]: item for item in manifest["defects"]}
    truth_rows = {item["defect_id"]: item for item in truth["positive_defects"]}
    if len(manifest_rows) != 15 or len(truth_rows) != 15:
        raise ValueError("Ground truth must contain exactly 15 positive P0 defect instances.")
    if set(manifest_rows) != set(truth_rows):
        raise ValueError("The injection manifest and ground truth defect IDs differ.")
    if truth["dataset_id"] != manifest["dataset_id"]:
        raise ValueError("Ground truth and injection manifest identify different datasets.")
    if truth["matching"] != _MATCHING_CONTRACT:
        raise ValueError("Ground truth matching contract differs from the benchmark matcher.")
    if truth["clean_controls"] != manifest["clean_controls"]:
        raise ValueError("Ground-truth controls differ from the injection manifest.")
    if truth["not_evaluated_p1"] != manifest["catalogue_exclusions"]:
        raise ValueError("P1 exclusions differ from the injection manifest.")
    checks = {(item["rule_id"], item["check_id"]): item for item in manifest["checks"]}
    for defect_id, label in truth_rows.items():
        injection = manifest_rows[defect_id]
        if label["priority"] != "P0" or injection["priority"] != "P0":
            raise ValueError(f"{defect_id} is not a P0 positive defect.")
        for field in (
            "global_ids",
            "element_name",
            "ifc_type",
            "injected_change",
            "requirement_id",
            "rule_id",
            "check_id",
            "rule_version",
            "rule_family",
            "expected_observed_evidence",
            "expected_result",
            "priority",
        ):
            if label[field] != injection[field]:
                raise ValueError(
                    f"{defect_id} ground-truth field {field!r} differs from its manifest."
                )
        if (label["rule_id"], label["check_id"]) not in checks:
            raise ValueError(
                f"{defect_id} references a check absent from the implemented registry."
            )
    control_ids = {item["global_id"] for item in truth["clean_controls"]}
    defect_global_ids = {
        global_id for item in truth["positive_defects"] for global_id in item["global_ids"]
    }
    if control_ids.intersection(defect_global_ids):
        raise ValueError("A GlobalId cannot be both a positive defect and a clean control.")
    if len(defect_global_ids) != len(truth["positive_defects"]):
        raise ValueError("Positive defect GlobalIds must be independently unique.")
    clean_bytes = artifacts.clean_ifc.read_bytes()
    defective_bytes = artifacts.defective_ifc.read_bytes()
    if truth["defect_model_sha256"] != hashlib.sha256(defective_bytes).hexdigest():
        raise ValueError("Ground truth is bound to a different defective IFC hash.")
    _verify_clean_and_injected_facts(clean_bytes, defective_bytes, manifest["defects"])


def metrics(
    expected: list[dict[str, Any]], predicted: list[dict[str, Any]]
) -> dict[str, int | float | None]:
    """Compute one-to-one exact rule/GlobalId-set matching with duplicate predictions as FP."""
    remaining = [_finding_key(item) for item in expected]
    true_positives = 0
    false_positives = 0
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for prediction in predicted:
        key = _finding_key(prediction)
        if key in seen:
            false_positives += 1
            continue
        seen.add(key)
        try:
            remaining.remove(key)
        except ValueError:
            false_positives += 1
        else:
            true_positives += 1
    false_negatives = len(remaining)
    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives
        else None
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives
        else None
    )
    f1_denominator = 2 * true_positives + false_positives + false_negatives
    f1 = 2 * true_positives / f1_denominator if f1_denominator else None
    return {
        "tp": true_positives,
        "fp": false_positives,
        "fn": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def finding_record(finding: Any) -> dict[str, Any]:
    """Reduce a canonical Finding to the identity used by the benchmark matcher."""
    return {
        "rule_id": finding.rule_id,
        "check_id": finding.check_id,
        "global_ids": sorted(element.global_id for element in finding.elements),
        "finding_id": finding.id,
        "category": finding.category,
        "method": finding.method,
    }


def control_false_positives(
    predicted: list[dict[str, Any]], controls: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    control_ids = {item["global_id"] for item in controls}
    return [
        prediction
        for prediction in predicted
        if control_ids.intersection(_finding_key(prediction)[2])
    ]


def _finding_key(record: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    ids = record.get("global_ids")
    if ids is None:
        ids = [element["global_id"] for element in record.get("elements", [])]
    return (
        str(record["rule_id"]),
        str(record.get("check_id", "")),
        tuple(sorted(str(item) for item in ids)),
    )


def _property_spec(
    identifier: str,
    title: str,
    entity: str,
    property_set: str,
    property_name: str,
    pattern: str | None = None,
) -> ifctester.ids.Specification:
    spec = _spec(identifier, title)
    spec.applicability.append(ifctester.ids.Entity(name=entity))
    value = Restriction({"pattern": pattern}) if pattern else None
    spec.requirements.append(
        ifctester.ids.Property(
            propertySet=property_set,
            baseName=property_name,
            value=value,
            dataType="IFCLABEL" if pattern else None,
            cardinality="required",
        )
    )
    return spec


def _external_wall_applicability_spec() -> ifctester.ids.Specification:
    spec = _spec(
        "IDS:external_wall_applicability",
        "External wall requirement applicability control",
    )
    spec.applicability.append(ifctester.ids.Entity(name="IFCWALL"))
    spec.applicability.append(
        ifctester.ids.Property(
            propertySet="Pset_WallCommon",
            baseName="IsExternal",
            value="true",
            dataType="IFCBOOLEAN",
        )
    )
    spec.requirements.append(
        ifctester.ids.Property(
            propertySet="Pset_WallCommon",
            baseName="LoadBearing",
            cardinality="required",
        )
    )
    return spec


def _attribute_spec(
    identifier: str, title: str, entity: str, pattern: str
) -> ifctester.ids.Specification:
    spec = _spec(identifier, title)
    spec.applicability.append(ifctester.ids.Entity(name=entity))
    spec.requirements.append(
        ifctester.ids.Attribute(
            name="Name",
            value=Restriction({"pattern": pattern}),
            cardinality="required",
        )
    )
    return spec


def _classification_spec(identifier: str, title: str, entity: str) -> ifctester.ids.Specification:
    spec = _spec(identifier, title)
    spec.applicability.append(ifctester.ids.Entity(name=entity))
    spec.requirements.append(
        ifctester.ids.Classification(system=CLASSIFICATION_SYSTEM, cardinality="required")
    )
    return spec


def _spec(identifier: str, title: str) -> ifctester.ids.Specification:
    return ifctester.ids.Specification(
        name=identifier,
        identifier=identifier,
        description=title,
        ifcVersion=["IFC4"],
        minOccurs=1,
        maxOccurs="unbounded",
    )


def _build_model() -> ifcopenshell.file:
    model = ifcopenshell.api.project.create_file(version="IFC4")
    _fix_header(model)
    project = _create(model, "IfcProject", "BIM Intelligence Benchmark")
    ifcopenshell.api.unit.assign_unit(model, length={"is_metric": True, "raw": "METERS"})
    model_context = ifcopenshell.api.context.add_context(model, context_type="Model")
    body_context = ifcopenshell.api.context.add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )
    site = _create(model, "IfcSite", "Benchmark Site")
    building = _create(model, "IfcBuilding", "Benchmark Building")
    storeys = [_create(model, "IfcBuildingStorey", f"L{index:02d}") for index in range(3)]
    ifcopenshell.api.aggregate.assign_object(model, products=[site], relating_object=project)
    ifcopenshell.api.aggregate.assign_object(model, products=[building], relating_object=site)
    for level, storey in enumerate(storeys):
        ifcopenshell.api.aggregate.assign_object(model, products=[storey], relating_object=building)
        _set_placement(model, storey, (0.0, 0.0, level * 3.5))

    uniclass = ifcopenshell.api.classification.add_classification(
        model, classification=CLASSIFICATION_SYSTEM
    )
    ifcopenshell.api.classification.add_classification(
        model, classification=WRONG_CLASSIFICATION_SYSTEM
    )
    wall_type = _create(model, "IfcWallType", "WT-CLASSIFIED")
    ifcopenshell.api.classification.add_reference(
        model,
        products=[wall_type],
        identification="Ss_25_10_30",
        name="Wall systems",
        classification=uniclass,
    )

    def add_product(
        ifc_class: str,
        name: str,
        storey: ifcopenshell.entity_instance,
        *,
        origin: tuple[float, float, float],
        dimensions: tuple[float, float, float],
        pset_name: str,
        properties: dict[str, object],
        classification: str = "Ss_25_10_30",
        classification_system: Any = uniclass,
        description: str | None = None,
    ) -> ifcopenshell.entity_instance:
        product = _create(model, ifc_class, name)
        if description is not None:
            product.Description = description
        if ifc_class == "IfcSpace":
            ifcopenshell.api.aggregate.assign_object(
                model, products=[product], relating_object=storey
            )
        else:
            ifcopenshell.api.spatial.assign_container(
                model, products=[product], relating_structure=storey
            )
        _set_placement(model, product, origin)
        representation = ifcopenshell.api.geometry.add_wall_representation(
            model,
            context=body_context,
            length=dimensions[0],
            height=dimensions[1],
            thickness=dimensions[2],
        )
        ifcopenshell.api.geometry.assign_representation(
            model, product=product, representation=representation
        )
        pset = ifcopenshell.api.pset.add_pset(model, product=product, name=pset_name)
        ifcopenshell.api.pset.edit_pset(model, pset=pset, properties=properties)
        ifcopenshell.api.classification.add_reference(
            model,
            products=[product],
            identification=classification,
            name=f"{ifc_class} classification",
            classification=classification_system,
        )
        return product

    walls: dict[str, ifcopenshell.entity_instance] = {}
    for index in range(1, 13):
        name = "W-012-EXT" if index == 12 else f"W-{index:03d}"
        wall = add_product(
            "IfcWall",
            name,
            storeys[(index - 1) % len(storeys)],
            origin=((index - 1) * 1.2, 0.0, 0.0),
            dimensions=(1.0, 3.0, 0.2),
            pset_name="Pset_WallCommon",
            properties={
                "IsExternal": index != 12,
                "FireRating": "REI 60",
                "LoadBearing": True,
            },
            description="External design intent; IsExternal intentionally false."
            if index == 12
            else None,
        )
        walls[name] = wall
    for name in ("W-008", "W-012-EXT"):
        ifcopenshell.api.type.assign_type(
            model, related_objects=[walls[name]], relating_type=wall_type
        )

    for index in range(1, 7):
        add_product(
            "IfcDoor",
            f"D-{index:03d}",
            storeys[(index - 1) % len(storeys)],
            origin=((index - 1) * 2.0, 2.0, 0.0),
            dimensions=(0.9, 2.1, 0.1),
            pset_name="Pset_DoorCommon",
            properties={"IsExternal": True, "FireRating": "REI 60"},
        )
    for index in range(1, 7):
        add_product(
            "IfcWindow",
            f"WN-{index:03d}",
            storeys[(index - 1) % len(storeys)],
            origin=((index - 1) * 2.0, 4.0, 1.0),
            dimensions=(1.2, 1.2, 0.1),
            pset_name="Pset_WindowCommon",
            properties={"IsExternal": True},
        )
    for index in range(1, 4):
        add_product(
            "IfcSlab",
            f"SL-{index:03d}",
            storeys[index - 1],
            origin=(0.0, 8.0, 0.0),
            dimensions=(4.0, 0.2, 4.0),
            pset_name="Pset_SlabCommon",
            properties={"IsExternal": False},
        )
        add_product(
            "IfcSpace",
            f"SP-{index:03d}",
            storeys[index - 1],
            origin=(0.0, 12.0, 0.0),
            dimensions=(4.0, 3.0, 4.0),
            pset_name="Pset_SpaceCommon",
            properties={"Reference": f"ROOM-{index:03d}", "LongName": f"Room {index}"},
        )

    for index, root in enumerate(model.by_type("IfcRoot")):
        if root is project:
            root.GlobalId = deterministic_guid("project")
        elif root.is_a("IfcProduct"):
            root.GlobalId = deterministic_guid(root.Name or f"product:{root.id()}")
        else:
            root.GlobalId = deterministic_guid(
                f"root:{index}:{root.is_a()}:{getattr(root, 'Name', '') or ''}"
            )
    _assert_unique_global_ids(model)
    return model


def _set_placement(
    model: ifcopenshell.file,
    product: ifcopenshell.entity_instance,
    origin: tuple[float, float, float],
) -> None:
    placement = np.eye(4)
    placement[:3, 3] = origin
    ifcopenshell.api.geometry.edit_object_placement(model, product=product, matrix=placement)


def _inject_defects(model: ifcopenshell.file, checks_by_id: dict[str, Any]) -> list[dict[str, Any]]:
    defects = (
        _defect(
            "D01",
            "W-001",
            "IfcWall",
            "Remove Pset_WallCommon.FireRating.",
            "property.required",
            "IDS:wall_fire_rating",
            "FireRating property is absent.",
            lambda: _remove_property(model, "IfcWall", "W-001", "Pset_WallCommon", "FireRating"),
        ),
        _defect(
            "D02",
            "W-002",
            "IfcWall",
            "Remove Pset_WallCommon.FireRating.",
            "property.required",
            "IDS:wall_fire_rating",
            "FireRating property is absent.",
            lambda: _remove_property(model, "IfcWall", "W-002", "Pset_WallCommon", "FireRating"),
        ),
        _defect(
            "D03",
            "D-003",
            "IfcDoor",
            "Set Pset_DoorCommon.FireRating to an empty string.",
            "property.required",
            "IDS:door_fire_rating",
            "FireRating property value is empty.",
            lambda: _set_property(model, "IfcDoor", "D-003", "Pset_DoorCommon", "FireRating", ""),
        ),
        _defect(
            "D04",
            "W-003",
            "IfcWall",
            'Set Pset_WallCommon.FireRating to "TBC".',
            "property.required",
            "IDS:wall_fire_rating",
            'FireRating property value is "TBC".',
            lambda: _set_property(
                model, "IfcWall", "W-003", "Pset_WallCommon", "FireRating", "TBC"
            ),
        ),
        _defect(
            "D05",
            "W-004",
            "IfcWall",
            "Remove Pset_WallCommon from the wall occurrence.",
            "property.required",
            "IDS:wall_fire_rating",
            "Pset_WallCommon is absent.",
            lambda: _remove_pset(model, "IfcWall", "W-004", "Pset_WallCommon"),
        ),
        _defect(
            "D06",
            "SP-001",
            "IfcSpace",
            "Remove Pset_SpaceCommon from the space occurrence.",
            "property.required",
            "IDS:space_reference",
            "Pset_SpaceCommon is absent.",
            lambda: _remove_pset(model, "IfcSpace", "SP-001", "Pset_SpaceCommon"),
        ),
        _defect(
            "D07",
            "W-005",
            "IfcWall",
            'Rename the wall to "Wall 005".',
            "naming.pattern",
            "IDS:wall_name",
            'Name is "Wall 005", not W-###.',
            lambda: _rename(model, "IfcWall", "W-005", "Wall 005"),
        ),
        _defect(
            "D08",
            "W-006",
            "IfcWall",
            'Rename the wall to "W-06".',
            "naming.pattern",
            "IDS:wall_name",
            'Name is "W-06", not W-###.',
            lambda: _rename(model, "IfcWall", "W-006", "W-06"),
        ),
        _defect(
            "D09",
            "L01",
            "IfcBuildingStorey",
            'Rename storey L01 to "Level 1".',
            "naming.pattern",
            "IDS:storey_name",
            'Name is "Level 1", not L##.',
            lambda: _rename(model, "IfcBuildingStorey", "L01", "Level 1"),
        ),
        _defect(
            "D10",
            "D-005",
            "IfcDoor",
            'Rename the door to "Door 005".',
            "naming.pattern",
            "IDS:door_name",
            'Name is "Door 005", not D-###.',
            lambda: _rename(model, "IfcDoor", "D-005", "Door 005"),
        ),
        _defect(
            "D11",
            "WN-001",
            "IfcWindow",
            "Remove the window's classification reference.",
            "classification.*",
            "IDS:window_classification",
            "No classification reference is present.",
            lambda: _remove_classifications(model, "IfcWindow", "WN-001"),
        ),
        _defect(
            "D12",
            "WN-002",
            "IfcWindow",
            "Remove the window's classification reference.",
            "classification.*",
            "IDS:window_classification",
            "No classification reference is present.",
            lambda: _remove_classifications(model, "IfcWindow", "WN-002"),
        ),
        _defect(
            "D13",
            "W-007",
            "IfcWall",
            "Replace the Uniclass classification with a different system.",
            "classification.*",
            "IDS:wall_classification",
            f"Classification uses {WRONG_CLASSIFICATION_SYSTEM}, not {CLASSIFICATION_SYSTEM}.",
            lambda: _set_classification_system(model, "IfcWall", "W-007"),
        ),
        _defect(
            "D14",
            "W-008",
            "IfcWall",
            "Change the occurrence code to WRONG-CODE while its type remains Ss_25_10_30.",
            "classification.*",
            CLASSIFICATION_CONSISTENCY_RULE_ID,
            "Occurrence classification is WRONG-CODE; type classification is Ss_25_10_30.",
            lambda: _set_classification_code(model, "IfcWall", "W-008"),
        ),
        _defect(
            "D19",
            "W-009",
            "IfcWall",
            "Remove Pset_WallCommon.FireRating as an additional independently labelled instance.",
            "property.required",
            "IDS:wall_fire_rating",
            "FireRating property is absent.",
            lambda: _remove_property(model, "IfcWall", "W-009", "Pset_WallCommon", "FireRating"),
        ),
    )
    results: list[dict[str, Any]] = []
    for (
        defect_id,
        element_name,
        ifc_type,
        injection,
        family,
        check_name,
        observed,
        apply,
    ) in defects:
        element = _by_name(model, ifc_type, element_name)
        apply()
        results.append(
            {
                "defect_id": defect_id,
                "global_ids": [element.GlobalId],
                "element_name": element_name,
                "ifc_type": ifc_type,
                "injected_change": injection,
                "requirement_id": _requirement_id(family),
                "rule_family": family,
                "check_name": check_name,
                "rule_id": (
                    CLASSIFICATION_CONSISTENCY_RULE_ID
                    if check_name == CLASSIFICATION_CONSISTENCY_RULE_ID
                    else f"ids:{check_name}"
                ),
                "rule_version": (
                    CLASSIFICATION_CONSISTENCY_RULE_VERSION
                    if check_name == CLASSIFICATION_CONSISTENCY_RULE_ID
                    else checks_by_id[check_name].rule_version
                ),
                "check_id": (
                    classification_consistency_check().id
                    if check_name == CLASSIFICATION_CONSISTENCY_RULE_ID
                    else checks_by_id[check_name].id
                ),
                "expected_result": "failed",
                "expected_observed_evidence": observed,
                "priority": "P0",
            }
        )
    return results


def _defect(
    defect_id: str,
    element_name: str,
    ifc_type: str,
    injection: str,
    family: str,
    check_name: str,
    observed: str,
    apply: Any,
) -> tuple[str, str, str, str, str, str, str, Any]:
    return defect_id, element_name, ifc_type, injection, family, check_name, observed, apply


def _requirement_id(rule_family: str) -> str:
    return {
        "property.required": "FR-VAL-02",
        "naming.pattern": "FR-VAL-03",
        "classification.*": "FR-VAL-04",
        CLASSIFICATION_CONSISTENCY_RULE_ID: "FR-VAL-04",
    }[rule_family]


def _manifest_payload(
    defects: list[dict[str, Any]], checks_by_id: dict[str, Any]
) -> dict[str, Any]:
    controls = _controls()
    checks = [
        {
            "check_name": name.removeprefix("IDS:"),
            "rule_id": checks_by_id[name].rule_id,
            "check_id": checks_by_id[name].id,
            "rule_version": checks_by_id[name].rule_version,
            "rule_family": _CHECK_FAMILIES[name],
            "implemented": True,
            "applicability_control": name == "IDS:column_non_applicability",
        }
        for name in sorted(checks_by_id)
    ]
    checks.append(
        {
            "check_name": CLASSIFICATION_CONSISTENCY_RULE_ID,
            "rule_id": CLASSIFICATION_CONSISTENCY_RULE_ID,
            "check_id": classification_consistency_check().id,
            "rule_version": CLASSIFICATION_CONSISTENCY_RULE_VERSION,
            "rule_family": "classification.*",
            "implemented": True,
            "applicability_control": False,
        }
    )
    return {
        "manifest_version": MANIFEST_VERSION,
        "dataset_id": "bim-intelligence-synthetic-architectural-v1",
        "ifc_schema": "IFC4",
        "checks": checks,
        "defects": defects,
        "clean_controls": controls,
        "catalogue_exclusions": _catalogue_exclusions(),
        "supported_p0_categories": [
            "FR-VAL-02 property requiredness and value patterns",
            "FR-VAL-03 expressible naming patterns",
            "FR-VAL-04 classification system/presence and type-occurrence consistency",
        ],
        "unsupported_p0_categories": [],
        "unsupported_p1_categories": [
            {
                "requirement_id": "FR-VAL-05",
                "category": "spatial.contained",
                "reason": "P1; no registered relationship-validity check is implemented.",
            },
            {
                "requirement_id": "FR-VAL-06",
                "category": "identity.unique_global_id",
                "reason": "P1; no registered duplicate/malformed GlobalId check is implemented.",
            },
        ],
        "not_counted_as_p0": ["D15", "D16", "D17", "D18"],
    }


def _ground_truth_payload(
    defects: list[dict[str, Any]], checks_by_id: dict[str, Any], defective_bytes: bytes
) -> dict[str, Any]:
    positive = [
        {
            "defect_id": defect["defect_id"],
            "global_ids": defect["global_ids"],
            "element_name": defect["element_name"],
            "ifc_type": defect["ifc_type"],
            "injected_change": defect["injected_change"],
            "requirement_id": defect["requirement_id"],
            "rule_id": defect["rule_id"],
            "check_id": defect["check_id"],
            "rule_version": defect["rule_version"],
            "rule_family": defect["rule_family"],
            "expected_observed_evidence": defect["expected_observed_evidence"],
            "expected_result": defect["expected_result"],
            "priority": defect["priority"],
        }
        for defect in defects
    ]
    return {
        "ground_truth_version": MANIFEST_VERSION,
        "dataset_id": "bim-intelligence-synthetic-architectural-v1",
        "defect_model_sha256": hashlib.sha256(defective_bytes).hexdigest(),
        "matching": _MATCHING_CONTRACT,
        "positive_defects": positive,
        "clean_controls": _controls(),
        "not_evaluated_p1": _catalogue_exclusions(),
        "non_applicable_controls": [
            {
                "check_name": "IDS:column_non_applicability",
                "rule_id": checks_by_id["IDS:column_non_applicability"].rule_id,
                "expected_status": "not_applicable",
                "expected_findings": 0,
            }
        ],
    }


def _controls() -> list[dict[str, Any]]:
    controls = [
        ("C01", "W-010", "IfcWall", "compliant wall with matching type classification"),
        ("C02", "D-006", "IfcDoor", "compliant door with a valid fire rating and name"),
        ("C03", "WN-003", "IfcWindow", "compliant window with project classification"),
        ("C04", "SL-001", "IfcSlab", "compliant slab with spatial containment"),
        ("C05", "SP-002", "IfcSpace", "compliant space with Pset_SpaceCommon.Reference"),
        ("C06", "L02", "IfcBuildingStorey", "compliant storey name"),
        (
            "D18",
            "W-012-EXT",
            "IfcWall",
            (
                "Name marks an external wall, but IsExternal=false; "
                "must not match an external-only check."
            ),
        ),
    ]
    return [
        {
            "control_id": control_id,
            "global_id": deterministic_guid(element_name),
            "element_name": element_name,
            "ifc_type": ifc_type,
            "expected_result": "no_finding",
            "description": description,
        }
        for control_id, element_name, ifc_type, description in controls
    ]


def _catalogue_exclusions() -> list[dict[str, Any]]:
    return [
        {
            "defect_id": "D15",
            "priority": "P1",
            "target_global_ids": [deterministic_guid("D-001")],
            "injected_change": "Not injected: remove the door's spatial containment.",
            "requirement_id": "FR-VAL-05",
            "rule_id": "spatial.contained",
            "check_id": None,
            "expected_result": "not_evaluated",
            "expected_observed_evidence": "Not observed; the registered rule is unimplemented.",
            "implemented": False,
        },
        {
            "defect_id": "D16",
            "priority": "P1",
            "target_global_ids": [deterministic_guid("W-011")],
            "injected_change": "Not injected: contain the wall in the wrong storey.",
            "requirement_id": "FR-VAL-05",
            "rule_id": "spatial.contained",
            "check_id": None,
            "expected_result": "not_evaluated",
            "expected_observed_evidence": "Not observed; the registered rule is unimplemented.",
            "implemented": False,
        },
        {
            "defect_id": "D17",
            "priority": "P1",
            "target_global_ids": [
                deterministic_guid("WN-004"),
                deterministic_guid("WN-005"),
            ],
            "injected_change": "Not injected: duplicate the GlobalId of one window.",
            "requirement_id": "FR-VAL-06",
            "rule_id": "identity.unique_global_id",
            "check_id": None,
            "expected_result": "not_evaluated",
            "expected_observed_evidence": "Not observed; the registered rule is unimplemented.",
            "implemented": False,
        },
    ]


def _verify_clean_and_injected_facts(
    clean_bytes: bytes, defective_bytes: bytes, defects: list[dict[str, Any]]
) -> None:
    clean = ifcopenshell.file.from_string(clean_bytes.decode("utf-8"))
    defective = ifcopenshell.file.from_string(defective_bytes.decode("utf-8"))
    if len(defects) != 15 or len({d["defect_id"] for d in defects}) != 15:
        raise ValueError("The benchmark must contain exactly 15 unique P0 defect instances.")
    if any(not _has_clean_requirement_facts(clean, control) for control in _controls()):
        raise ValueError("A declared clean control does not match the clean IFC facts.")
    for defect in defects:
        elements = [
            element.GlobalId in defect["global_ids"] and element.is_a() == defect["ifc_type"]
            for element in defective.by_type(defect["ifc_type"])
        ]
        if not any(elements):
            raise ValueError(f"{defect['defect_id']} GlobalId is absent from the defective IFC.")
        element = next(
            item
            for item in defective.by_type(defect["ifc_type"])
            if item.GlobalId == defect["global_ids"][0]
        )
        _verify_defect_fact(defective, element, defect["defect_id"])
    if any(not _has_clean_requirement_facts(defective, control) for control in _controls()):
        raise ValueError("A declared clean control was changed by defect injection.")
    if len({root.GlobalId for root in defective.by_type("IfcRoot")}) != len(
        defective.by_type("IfcRoot")
    ):
        raise ValueError("The defective IFC contains duplicate GlobalIds.")


def _verify_defect_fact(
    model: ifcopenshell.file, element: ifcopenshell.entity_instance, defect_id: str
) -> None:
    property_cases = {
        "D01": ("Pset_WallCommon", "FireRating", None),
        "D02": ("Pset_WallCommon", "FireRating", None),
        "D03": ("Pset_DoorCommon", "FireRating", ""),
        "D04": ("Pset_WallCommon", "FireRating", "TBC"),
        "D19": ("Pset_WallCommon", "FireRating", None),
    }
    if defect_id in property_cases:
        pset_name, property_name, expected = property_cases[defect_id]
        pset = _pset(element, pset_name)
        if expected is None:
            if pset is None or _property_value(pset, property_name) is not None:
                raise ValueError(f"{defect_id} injection facts did not persist.")
        elif pset is None or _property_value(pset, property_name) != expected:
            raise ValueError(f"{defect_id} injected property value did not persist.")
        return
    if defect_id == "D05" and _pset(element, "Pset_WallCommon") is not None:
        raise ValueError("D05 Pset removal did not persist.")
    if defect_id == "D06" and _pset(element, "Pset_SpaceCommon") is not None:
        raise ValueError("D06 Pset removal did not persist.")
    expected_names = {
        "D07": "Wall 005",
        "D08": "W-06",
        "D09": "Level 1",
        "D10": "Door 005",
    }
    if defect_id in expected_names and element.Name != expected_names[defect_id]:
        raise ValueError(f"{defect_id} injected name did not persist.")
    if defect_id in {"D11", "D12"} and _has_classification_system(element, CLASSIFICATION_SYSTEM):
        raise ValueError(f"{defect_id} classification removal did not persist.")
    if defect_id == "D13" and (
        _has_classification_system(element, CLASSIFICATION_SYSTEM)
        or not _has_classification_system(element, WRONG_CLASSIFICATION_SYSTEM)
    ):
        raise ValueError("D13 wrong-system classification did not persist.")
    if defect_id == "D14":
        type_ref = next(
            item.RelatingType for item in element.IsTypedBy if item.is_a("IfcRelDefinesByType")
        )
        if _direct_classification_code(element) != "WRONG-CODE" or (
            _direct_classification_code(type_ref) != "Ss_25_10_30"
        ):
            raise ValueError("D14 occurrence/type classification mismatch did not persist.")


def _direct_classification_code(product: ifcopenshell.entity_instance) -> str | None:
    for relationship in getattr(product, "HasAssociations", ()):
        if relationship.is_a("IfcRelAssociatesClassification"):
            return getattr(relationship.RelatingClassification, "Identification", None)
    return None


def _has_clean_requirement_facts(model: ifcopenshell.file, control: dict[str, Any]) -> bool:
    element = _by_name(model, control["ifc_type"], control["element_name"])
    if control["control_id"] == "D18":
        pset = _pset(element, "Pset_WallCommon")
        return bool(
            pset
            and _property_value(pset, "IsExternal") is False
            and _property_value(pset, "LoadBearing") is True
            and element.Name == "W-012-EXT"
        )
    if control["ifc_type"] == "IfcWall":
        pset = _pset(element, "Pset_WallCommon")
        return bool(
            pset
            and _property_value(pset, "FireRating") == "REI 60"
            and element.Name == f"W-{int(element.Name[2:]):03d}"
        )
    if control["ifc_type"] == "IfcDoor":
        pset = _pset(element, "Pset_DoorCommon")
        return bool(pset and _property_value(pset, "FireRating") == "REI 60")
    if control["ifc_type"] == "IfcWindow":
        return _has_classification_system(element, CLASSIFICATION_SYSTEM)
    if control["ifc_type"] == "IfcSpace":
        pset = _pset(element, "Pset_SpaceCommon")
        return bool(pset and _property_value(pset, "Reference"))
    if control["ifc_type"] == "IfcBuildingStorey":
        return bool(element.Name and len(element.Name) == 3 and element.Name.startswith("L"))
    return True


def _remove_property(
    model: ifcopenshell.file, ifc_type: str, name: str, pset_name: str, property_name: str
) -> None:
    pset = _required_pset(model, ifc_type, name, pset_name)
    properties = list(pset.HasProperties)
    matching = [prop for prop in properties if prop.Name == property_name]
    if len(matching) != 1:
        raise ValueError(f"Expected one {property_name} property on {name}.")
    pset.HasProperties = tuple(prop for prop in properties if prop.Name != property_name)
    model.remove(matching[0])


def _set_property(
    model: ifcopenshell.file,
    ifc_type: str,
    name: str,
    pset_name: str,
    property_name: str,
    value: str,
) -> None:
    pset = _required_pset(model, ifc_type, name, pset_name)
    matching = [prop for prop in pset.HasProperties if prop.Name == property_name]
    if len(matching) != 1:
        raise ValueError(f"Expected one {property_name} property on {name}.")
    ifcopenshell.api.pset.edit_pset(model, pset=pset, properties={property_name: value})


def _remove_pset(model: ifcopenshell.file, ifc_type: str, name: str, pset_name: str) -> None:
    element = _by_name(model, ifc_type, name)
    pset = _required_pset(model, ifc_type, name, pset_name)
    for relationship in list(model.by_type("IfcRelDefinesByProperties")):
        if relationship.RelatingPropertyDefinition == pset:
            relationship.RelatedObjects = tuple(
                item for item in relationship.RelatedObjects if item != element
            )
            if not relationship.RelatedObjects:
                model.remove(relationship)
    model.remove(pset)


def _rename(model: ifcopenshell.file, ifc_type: str, old_name: str, new_name: str) -> None:
    _by_name(model, ifc_type, old_name).Name = new_name


def _remove_classifications(model: ifcopenshell.file, ifc_type: str, name: str) -> None:
    element = _by_name(model, ifc_type, name)
    for relationship in list(model.by_type("IfcRelAssociatesClassification")):
        if element in relationship.RelatedObjects:
            relationship.RelatedObjects = tuple(
                item for item in relationship.RelatedObjects if item != element
            )
            if not relationship.RelatedObjects:
                model.remove(relationship)


def _set_classification_system(model: ifcopenshell.file, ifc_type: str, name: str) -> None:
    element = _by_name(model, ifc_type, name)
    _remove_classifications(model, ifc_type, name)
    system = next(
        item
        for item in model.by_type("IfcClassification")
        if item.Name == WRONG_CLASSIFICATION_SYSTEM
    )
    ifcopenshell.api.classification.add_reference(
        model,
        products=[element],
        identification="WALL-WRONG",
        name="Wrong system wall",
        classification=system,
    )


def _set_classification_code(model: ifcopenshell.file, ifc_type: str, name: str) -> None:
    element = _by_name(model, ifc_type, name)
    _remove_classifications(model, ifc_type, name)
    system = next(
        item for item in model.by_type("IfcClassification") if item.Name == CLASSIFICATION_SYSTEM
    )
    ifcopenshell.api.classification.add_reference(
        model,
        products=[element],
        identification="WRONG-CODE",
        name="Wrong wall code",
        classification=system,
    )


def _pset(product: ifcopenshell.entity_instance, name: str) -> Any | None:
    for relationship in getattr(product, "IsDefinedBy", ()):
        if (
            relationship.is_a("IfcRelDefinesByProperties")
            and relationship.RelatingPropertyDefinition.is_a("IfcPropertySet")
            and relationship.RelatingPropertyDefinition.Name == name
        ):
            return relationship.RelatingPropertyDefinition
    return None


def _required_pset(model: ifcopenshell.file, ifc_type: str, name: str, pset_name: str) -> Any:
    pset = _pset(_by_name(model, ifc_type, name), pset_name)
    if pset is None:
        raise ValueError(f"{name} has no {pset_name}.")
    return pset


def _property_value(pset: Any, property_name: str) -> Any:
    for prop in pset.HasProperties:
        if prop.Name == property_name:
            return prop.NominalValue.wrappedValue
    return None


def _has_classification_system(product: ifcopenshell.entity_instance, system_name: str) -> bool:
    for relationship in getattr(product, "HasAssociations", ()):
        if relationship.is_a("IfcRelAssociatesClassification"):
            classification = relationship.RelatingClassification
            system = getattr(classification, "ReferencedSource", None) or classification
            if getattr(system, "Name", None) == system_name:
                return True
    return False


def _by_name(model: ifcopenshell.file, ifc_type: str, name: str) -> ifcopenshell.entity_instance:
    matches = [
        element for element in model.by_type(ifc_type) if getattr(element, "Name", None) == name
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one {ifc_type} named {name!r}, found {len(matches)}.")
    return matches[0]


def _fix_header(model: ifcopenshell.file) -> None:
    model.header.file_description.description = ("ViewDefinition[ReferenceView]",)
    model.header.file_name.name = "benchmark.ifc"
    model.header.file_name.time_stamp = _FIXED_TIMESTAMP
    model.header.file_name.author = ("BIM Intelligence synthetic benchmark",)
    model.header.file_name.organization = ("natnew/BIM-Intelligence",)
    model.header.file_name.preprocessor_version = "tests/evaluation/benchmark.py"
    model.header.file_name.originating_system = "BIM Intelligence"
    model.header.file_name.authorization = "none"


def _canonicalise_aggregates(model: ifcopenshell.file) -> None:
    unordered = {
        ifcopenshell.ifcopenshell_wrapper.aggregation_type.set_type,
        ifcopenshell.ifcopenshell_wrapper.aggregation_type.bag_type,
    }
    schema: Any = ifcopenshell.ifcopenshell_wrapper.schema_by_name(model.schema_identifier)
    for entity in model:
        declaration = schema.declaration_by_name(entity.is_a())
        derived = declaration.derived()
        for index, attribute in enumerate(declaration.all_attributes()):
            attribute_type = attribute.type_of_attribute()
            if derived[index] or not isinstance(
                attribute_type, ifcopenshell.ifcopenshell_wrapper.aggregation_type
            ):
                continue
            if attribute_type.type_of_aggregation() not in unordered:
                continue
            value = entity[index]
            if (
                isinstance(value, tuple)
                and value
                and all(isinstance(item, ifcopenshell.entity_instance) for item in value)
            ):
                entity[index] = tuple(sorted(value, key=lambda item: item.id()))


def _create(model: ifcopenshell.file, ifc_class: str, name: str) -> ifcopenshell.entity_instance:
    return ifcopenshell.api.root.create_entity(model, ifc_class=ifc_class, name=name)


def _assert_unique_global_ids(model: ifcopenshell.file) -> None:
    global_ids = [entity.GlobalId for entity in model.by_type("IfcRoot")]
    if len(global_ids) != len(set(global_ids)):
        raise ValueError("The generated IFC contains duplicate GlobalIds.")


def _pin_new_root_guids(model: ifcopenshell.file, existing_guids: dict[int, str]) -> None:
    for root in model.by_type("IfcRoot"):
        root.GlobalId = existing_guids.get(
            root.id(),
            deterministic_guid(f"generated:{root.is_a()}#{root.id()}"),
        )
    _assert_unique_global_ids(model)


def _ifc_bytes(model: ifcopenshell.file) -> bytes:
    return _lf_bytes(model.to_string())


def _lf_bytes(text: str) -> bytes:
    return text.replace("\r\n", "\n").encode("utf-8")


def _write_bytes(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def _write_text(path: Path, value: str) -> None:
    path.write_bytes(_lf_bytes(value))


def _write_json(path: Path, value: Any) -> None:
    _write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _benchmark_bep() -> str:
    return """# Synthetic benchmark BEP excerpt

This fictional project uses IFC4. The building has three storeys named `L00`, `L01` and
`L02`. Walls use `W-###` names, doors use `D-###` names and each storey follows `L##`.

Every wall and door must have a `FireRating` in its common property set matching `REI NN`.
Every space must declare `Pset_SpaceCommon.Reference`. Windows and walls must carry a
classification reference from **Uniclass 2015**.

When a wall occurrence is assigned a classified wall type, its classification reference must
match the type's reference. These requirements are synthetic, machine-checkable benchmark
clauses; they are not taken from a real project or standard contract.
"""


def _benchmark_objectives() -> list[dict[str, Any]]:
    return [
        {
            "objective": (
                "Check wall and door fire-rating values, including missing and placeholder data."
            ),
            "expected_rule_families": ["property.required"],
        },
        {
            "objective": "Check wall, door and storey naming patterns.",
            "expected_rule_families": ["naming.pattern"],
        },
        {
            "objective": "Check classification system coverage and wall type consistency.",
            "expected_rule_families": ["classification.*"],
        },
    ]


def _manifest_hashes(artifacts: BenchmarkArtifacts) -> dict[str, str]:
    """Return SHA-256 hashes for the generated inputs, for the evaluation report."""
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (
            artifacts.clean_ifc,
            artifacts.defective_ifc,
            artifacts.ids,
            artifacts.manifest,
            artifacts.ground_truth,
            artifacts.bep,
            artifacts.objectives,
        )
    }
