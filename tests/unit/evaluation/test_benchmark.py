from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import ifcopenshell
import pytest

from bim_intelligence.validation import compile_ids
from evaluation.benchmark import (
    control_false_positives,
    generate_benchmark,
    metrics,
    validate_ground_truth,
)
from fixtures.make_minimal_ifc import IFC_PATH


@pytest.fixture(scope="module")
def benchmark(tmp_path_factory: pytest.TempPathFactory) -> Any:
    return generate_benchmark(tmp_path_factory.mktemp("benchmark") / "generated")


def _finding(rule_id: str, check_id: str, global_id: str) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "check_id": check_id,
        "global_ids": [global_id],
    }


def test_generator_writes_realistic_ifc4_and_executable_ids(benchmark: Any) -> None:
    clean = ifcopenshell.open(str(benchmark.clean_ifc))
    assert clean.schema_identifier == "IFC4"
    assert len(clean.by_type("IfcBuildingStorey")) == 3
    assert len(clean.by_type("IfcWall")) >= 3
    assert clean.by_type("IfcDoor")
    assert clean.by_type("IfcWindow")
    assert clean.by_type("IfcSlab")
    assert clean.by_type("IfcSpace")
    assert clean.by_type("IfcRelContainedInSpatialStructure")
    assert clean.by_type("IfcRelDefinesByType")
    assert clean.by_type("IfcRelAssociatesClassification")
    assert clean.by_type("IfcShapeRepresentation")
    assert all(
        element.Representation is not None
        for ifc_type in ("IfcWall", "IfcDoor", "IfcWindow", "IfcSlab")
        for element in clean.by_type(ifc_type)
    )

    compiled = compile_ids(benchmark.ids.read_bytes())
    assert len(compiled.specifications) == 10
    assert {spec.name for spec in compiled.specifications} >= {
        "IDS:wall_fire_rating",
        "IDS:door_fire_rating",
        "IDS:space_reference",
        "IDS:wall_name",
        "IDS:door_name",
        "IDS:storey_name",
        "IDS:window_classification",
        "IDS:wall_classification",
        "IDS:external_wall_applicability",
        "IDS:column_non_applicability",
    }


def test_manifest_and_ground_truth_are_independently_consistent(benchmark: Any) -> None:
    validate_ground_truth(benchmark)
    manifest = json.loads(benchmark.manifest.read_text(encoding="utf-8"))
    ground_truth = json.loads(benchmark.ground_truth.read_text(encoding="utf-8"))
    defective = ifcopenshell.open(str(benchmark.defective_ifc))
    roots_by_guid = {root.GlobalId: root for root in defective.by_type("IfcRoot")}
    defect_rows = {item["defect_id"]: item for item in manifest["defects"]}
    truth_rows = {item["defect_id"]: item for item in ground_truth["positive_defects"]}

    assert len(defect_rows) == len(truth_rows) == 15
    assert set(defect_rows) == set(truth_rows)
    assert (
        len(
            {
                (row["rule_id"], row["check_id"], tuple(row["global_ids"]))
                for row in truth_rows.values()
            }
        )
        == 15
    )
    assert len({guid for row in truth_rows.values() for guid in row["global_ids"]}) == 15
    for defect_id, truth in truth_rows.items():
        manifest_row = defect_rows[defect_id]
        assert truth["priority"] == "P0"
        assert truth["rule_id"] == manifest_row["rule_id"]
        assert truth["check_id"] == manifest_row["check_id"]
        assert truth["global_ids"] == manifest_row["global_ids"]
        assert truth["rule_version"] == manifest_row["rule_version"]
        assert all(guid in roots_by_guid for guid in truth["global_ids"])
        assert truth["expected_observed_evidence"] == manifest_row["expected_observed_evidence"]

    control_ids = {row["global_id"] for row in ground_truth["clean_controls"]}
    defect_ids = {guid for row in truth_rows.values() for guid in row["global_ids"]}
    assert len(control_ids) == 7
    assert control_ids.isdisjoint(defect_ids)
    assert ground_truth["non_applicable_controls"][0]["expected_status"] == "not_applicable"
    assert [item["defect_id"] for item in ground_truth["not_evaluated_p1"]] == [
        "D15",
        "D16",
        "D17",
    ]
    assert manifest["unsupported_p0_categories"] == []
    assert ground_truth["matching"] == (
        "exact rule_id and check_id and exact sorted GlobalId set; one-to-one"
    )
    assert {item["requirement_id"] for item in manifest["unsupported_p1_categories"]} == {
        "FR-VAL-05",
        "FR-VAL-06",
    }

    # Confirm the labelled state directly from IFC facts, not from BIM Intelligence Findings.
    by_name = {
        row["element_name"]: roots_by_guid[row["global_ids"][0]] for row in truth_rows.values()
    }
    assert by_name["W-001"].is_a("IfcWall")  # type: ignore[no-untyped-call]
    assert by_name["W-003"].Name == "W-003"
    assert by_name["W-005"].Name == "Wall 005"
    assert by_name["L01"].Name == "Level 1"
    assert by_name["D-005"].Name == "Door 005"
    assert _property(by_name["D-003"], "Pset_DoorCommon", "FireRating") == ""
    assert _property(by_name["W-003"], "Pset_WallCommon", "FireRating") == "TBC"
    assert _property(by_name["W-001"], "Pset_WallCommon", "FireRating") is None
    assert not _has_pset(by_name["W-004"], "Pset_WallCommon")
    assert not _has_pset(by_name["SP-001"], "Pset_SpaceCommon")


def test_ground_truth_rejects_labels_that_differ_from_the_injection_manifest(
    tmp_path: Path,
) -> None:
    artifacts = generate_benchmark(tmp_path / "benchmark")
    ground_truth = json.loads(artifacts.ground_truth.read_text(encoding="utf-8"))
    ground_truth["positive_defects"][0]["expected_observed_evidence"] = "Incorrect label."
    artifacts.ground_truth.write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="expected_observed_evidence"):
        validate_ground_truth(artifacts)


def test_repeated_generation_is_byte_identical_and_does_not_touch_minimal_fixture(
    tmp_path: Path,
) -> None:
    before = hashlib.sha256(IFC_PATH.read_bytes()).hexdigest()
    first = generate_benchmark(tmp_path / "first")
    second = generate_benchmark(tmp_path / "second")
    first_paths = sorted(first.__dict__.values(), key=lambda path: path.name)
    second_by_name = {path.name: path for path in second.__dict__.values()}
    assert all(path.read_bytes() == second_by_name[path.name].read_bytes() for path in first_paths)
    assert hashlib.sha256(IFC_PATH.read_bytes()).hexdigest() == before


def test_metrics_handle_zero_predictions_and_zero_positive_defects() -> None:
    expected = [_finding("ids:rule-a", "check-a", "gid-a")]
    no_predictions = metrics(expected, [])
    assert no_predictions == {
        "tp": 0,
        "fp": 0,
        "fn": 1,
        "precision": None,
        "recall": 0.0,
        "f1": 0.0,
    }

    no_cases = metrics([], [])
    assert no_cases == {
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "precision": None,
        "recall": None,
        "f1": None,
    }


def test_duplicate_predictions_are_false_positives() -> None:
    expected = [_finding("ids:rule-a", "check-a", "gid-a")]
    result = metrics(expected, [expected[0], expected[0]])
    assert result["tp"] == 1
    assert result["fp"] == 1
    assert result["fn"] == 0
    assert result["precision"] == 0.5


@pytest.mark.parametrize(
    "prediction",
    [
        _finding("ids:rule-a", "check-a", "wrong-global-id"),
        _finding("ids:rule-b", "check-a", "gid-a"),
        _finding("ids:rule-a", "wrong-check", "gid-a"),
    ],
    ids=["incorrect-global-id", "wrong-rule", "correct-element-wrong-check"],
)
def test_identity_mismatches_are_one_false_positive_and_one_missed_defect(
    prediction: dict[str, Any],
) -> None:
    expected = [_finding("ids:rule-a", "check-a", "gid-a")]
    result = metrics(expected, [prediction])
    assert result["tp"] == 0
    assert result["fp"] == 1
    assert result["fn"] == 1


def test_multielement_findings_match_as_an_exact_unordered_global_id_set() -> None:
    expected = {
        "rule_id": "ids:grouped-rule",
        "check_id": "grouped-check",
        "global_ids": ["gid-b", "gid-a"],
    }
    predicted = {
        "rule_id": "ids:grouped-rule",
        "check_id": "grouped-check",
        "global_ids": ["gid-a", "gid-b"],
    }
    assert metrics([expected], [predicted])["tp"] == 1


def test_clean_control_predictions_are_explicit_false_positives() -> None:
    controls = [{"global_id": "control-guid"}]
    predictions = [_finding("ids:wall-name", "wall-name-check", "control-guid")]
    assert control_false_positives(predictions, controls) == predictions
    assert metrics([], predictions)["fp"] == 1


def _property(element: Any, pset_name: str, property_name: str) -> Any:
    for relationship in getattr(element, "IsDefinedBy", ()):
        if (
            relationship.is_a("IfcRelDefinesByProperties")
            and relationship.RelatingPropertyDefinition.Name == pset_name
        ):
            for prop in relationship.RelatingPropertyDefinition.HasProperties:
                if prop.Name == property_name:
                    return prop.NominalValue.wrappedValue
    return None


def _has_pset(element: Any, pset_name: str) -> bool:
    return any(
        relationship.is_a("IfcRelDefinesByProperties")
        and relationship.RelatingPropertyDefinition.Name == pset_name
        for relationship in getattr(element, "IsDefinedBy", ())
    )
