"""ElementRef and ModelSummary: the only way to refer to model elements (ADR-007, C-03)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bim_intelligence.schemas import ElementRef, ModelSummary

STOREY = ElementRef(
    global_id="0Rl8DF7rH3Z8m0CjaIvG4l", express_id=42, ifc_type="IfcBuildingStorey", name="L00"
)


def test_global_id_is_a_22_character_ifc_guid_when_present() -> None:
    ref = ElementRef(global_id="2O2Fr$t4X7Zf8NOew3FLKr", express_id=1, ifc_type="IfcWall")
    assert ref.global_id == "2O2Fr$t4X7Zf8NOew3FLKr"
    with pytest.raises(ValidationError):
        ElementRef(global_id="not-a-guid", express_id=1, ifc_type="IfcWall")
    with pytest.raises(ValidationError):
        ElementRef(global_id="", express_id=1, ifc_type="IfcWall")


def test_express_id_is_always_present_and_positive() -> None:
    ref = ElementRef(global_id=None, express_id=7, ifc_type="IfcPropertySet")
    assert ref.global_id is None
    assert ref.express_id == 7
    with pytest.raises(ValidationError):
        ElementRef(global_id=None, express_id=0, ifc_type="IfcPropertySet")


def test_key_prefers_global_id_and_falls_back_to_express_id() -> None:
    assert ElementRef(global_id="2O2Fr$t4X7Zf8NOew3FLKr", express_id=1, ifc_type="IfcWall").key == (
        "2O2Fr$t4X7Zf8NOew3FLKr"
    )
    assert ElementRef(global_id=None, express_id=7, ifc_type="IfcPropertySet").key == "#7"


def test_ifc_type_must_look_like_an_ifc_class_name() -> None:
    with pytest.raises(ValidationError):
        ElementRef(global_id=None, express_id=1, ifc_type="Wall")


def test_element_ref_is_immutable_and_hashable() -> None:
    ref = ElementRef(global_id=None, express_id=1, ifc_type="IfcWall")
    with pytest.raises(ValidationError):
        ref.name = "x"  # type: ignore[misc]
    assert len({ref, ElementRef(global_id=None, express_id=1, ifc_type="IfcWall")}) == 1


def test_model_summary_carries_schema_hash_counts_and_storeys() -> None:
    summary = ModelSummary(
        ifc_schema="IFC4",
        model_hash="f" * 64,
        project_name="Minimal",
        counts={"IfcWall": 3, "IfcBuildingStorey": 1},
        storeys=[STOREY],
    )
    assert summary.counts["IfcWall"] == 3
    assert summary.storeys[0].name == "L00"
    assert summary.element_count == 4


def test_model_hash_is_sha256_hex() -> None:
    with pytest.raises(ValidationError):
        ModelSummary(ifc_schema="IFC4", model_hash="abc", counts={}, storeys=[])


def test_counts_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        ModelSummary(ifc_schema="IFC4", model_hash="f" * 64, counts={"IfcWall": -1}, storeys=[])


def test_counts_keys_must_be_ifc_class_names() -> None:
    with pytest.raises(ValidationError, match="IFC class names"):
        ModelSummary(ifc_schema="IFC4", model_hash="f" * 64, counts={"Wall": 1}, storeys=[])
