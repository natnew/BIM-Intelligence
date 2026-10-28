"""ModelIndex construction against ``minimal.ifc`` and its variants (AC-03, FR-ING-02).

Every value the index exposes is cross-checked against IfcOpenShell's own utilities so the
index can never disagree with the model it summarises.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.classification
import ifcopenshell.util.element
import pytest

from bim_intelligence.bim import (
    AmbiguousGlobalIdError,
    InvalidGlobalIdError,
    ModelIndex,
    UnknownElementError,
    build_index,
    open_ifc,
)
from bim_intelligence.schemas import ElementRef
from fixtures.make_minimal_ifc import GLOBAL_IDS, IFC_PATH, WALLS
from fixtures.variants import (
    add_wall_type_with_inherited_properties,
    duplicate_w002_as_w001,
    malform_w003,
    write_ifc2x3,
    write_variant,
)

MODEL_HASH = hashlib.sha256(IFC_PATH.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def model() -> ifcopenshell.file:
    return open_ifc(IFC_PATH)


@pytest.fixture(scope="module")
def index(model: ifcopenshell.file) -> ModelIndex:
    return build_index(model, model_hash=MODEL_HASH)


@pytest.fixture
def ifc2x3_path(tmp_path: Path) -> Path:
    return write_ifc2x3(tmp_path)


class TestSummary:
    def test_headline_facts(self, index: ModelIndex) -> None:
        summary = index.summary
        assert summary.ifc_schema == "IFC4"
        assert summary.model_hash == MODEL_HASH
        assert summary.project_name == "Minimal Project"
        assert summary.counts == {
            "IfcSite": 1,
            "IfcBuilding": 1,
            "IfcBuildingStorey": 1,
            "IfcWall": 3,
        }
        assert summary.element_count == 6

    def test_storeys_in_file_order(self, index: ModelIndex) -> None:
        assert [s.name for s in index.summary.storeys] == ["L00"]
        storey = index.summary.storeys[0]
        assert storey.global_id == GLOBAL_IDS["L00"]
        assert storey.ifc_type == "IfcBuildingStorey"
        assert storey.storey is None


class TestWalls:
    def test_exactly_three_walls_with_pinned_names_and_global_ids(self, index: ModelIndex) -> None:
        walls = index.of_type("IfcWall")
        assert [w.ref.name for w in walls] == ["W-001", "W-002", "W-003"]
        assert [w.ref.global_id for w in walls] == [GLOBAL_IDS[w.name] for w in WALLS]
        assert all(w.ref.express_id >= 1 for w in walls)

    def test_lookup_by_global_id_and_express_id_agree(self, index: ModelIndex) -> None:
        record = index.by_global_id(GLOBAL_IDS["W-002"])
        assert record.ref.name == "W-002"
        assert index.by_express_id(record.ref.express_id) is record

    def test_containment_and_storey(self, index: ModelIndex, model: ifcopenshell.file) -> None:
        for wall in model.by_type("IfcWall"):
            record = index.by_global_id(wall.GlobalId)
            container = ifcopenshell.util.element.get_container(wall)
            assert record.container is not None and container is not None
            assert record.container.global_id == container.GlobalId
            assert record.container.ifc_type == "IfcBuildingStorey"
            assert record.ref.storey == "L00"
        storey = index.by_global_id(GLOBAL_IDS["L00"])
        assert storey.container is None and storey.ref.storey is None

    def test_property_sets_match_ifcopenshell_and_are_instance_owned(
        self, index: ModelIndex, model: ifcopenshell.file
    ) -> None:
        for wall in model.by_type("IfcWall"):
            record = index.by_global_id(wall.GlobalId)
            expected = _strip_ids(ifcopenshell.util.element.get_psets(wall))
            assert record.plain_psets() == expected, wall.Name
            assert all(
                prop.inherited is False
                for props in record.psets.values()
                for prop in props.values()
            )
        w001 = index.by_global_id(GLOBAL_IDS["W-001"]).psets["Pset_WallCommon"]
        assert w001["IsExternal"].value is True
        assert w001["FireRating"].value == "REI 60"
        w002 = index.by_global_id(GLOBAL_IDS["W-002"]).psets["Pset_WallCommon"]
        assert w002["IsExternal"].value is True
        assert "FireRating" not in w002
        w003 = index.by_global_id(GLOBAL_IDS["W-003"]).psets["Pset_WallCommon"]
        assert w003["IsExternal"].value is False
        assert w003["FireRating"].value == "REI 30"

    def test_classifications(self, index: ModelIndex) -> None:
        for name in ("W-001", "W-002"):
            refs = index.by_global_id(GLOBAL_IDS[name]).classifications
            assert len(refs) == 1
            assert refs[0].system == "Uniclass 2015"
            assert refs[0].identification == "Ss_25_10_30"
            assert refs[0].name == "Wall systems"
            assert refs[0].inherited is False
        assert index.by_global_id(GLOBAL_IDS["W-003"]).classifications == []

    def test_no_type_objects_in_the_baseline(self, index: ModelIndex) -> None:
        assert index.of_type("IfcWallType") == []
        assert all(w.type_ref is None for w in index.of_type("IfcWall"))
        assert all(w.predefined_type is None for w in index.of_type("IfcWall"))


class TestEveryIndexedEntity:
    def test_every_product_and_type_object_is_indexed_once(
        self, index: ModelIndex, model: ifcopenshell.file
    ) -> None:
        expected = {e.id() for e in model.by_type("IfcProduct")} | {
            e.id() for e in model.by_type("IfcTypeObject")
        }
        assert sorted(r.ref.express_id for r in index.elements) == sorted(expected)
        assert len({r.ref.express_id for r in index.elements}) == len(index.elements)

    def test_elements_are_ordered_by_express_id(self, index: ModelIndex) -> None:
        ids = [r.ref.express_id for r in index.elements]
        assert ids == sorted(ids)

    def test_psets_and_containers_match_ifcopenshell_for_every_record(
        self, index: ModelIndex, model: ifcopenshell.file
    ) -> None:
        for record in index.elements:
            entity = model.by_id(record.ref.express_id)
            assert record.plain_psets() == _strip_ids(ifcopenshell.util.element.get_psets(entity))
            container = ifcopenshell.util.element.get_container(entity)
            if container is None:
                assert record.container is None
            else:
                assert record.container is not None
                assert record.container.express_id == container.id()

    def test_no_duplicates_or_malformed_ids_in_the_baseline(self, index: ModelIndex) -> None:
        assert index.duplicate_global_ids == {}
        assert index.malformed_global_ids == {}


class TestLookupErrors:
    def test_unknown_global_id_raises(self, index: ModelIndex) -> None:
        with pytest.raises(UnknownElementError):
            index.by_global_id("0000000000000000000000")
        with pytest.raises(UnknownElementError):
            index.by_express_id(999_999)

    @pytest.mark.parametrize("bad", ["", "W-001", "21KH8X9wHPWw7JLiY2NtS", "../etc/passwd"])
    def test_malformed_global_id_is_rejected_before_lookup(
        self, index: ModelIndex, bad: str
    ) -> None:
        with pytest.raises(InvalidGlobalIdError):
            index.by_global_id(bad)


class TestDuplicateGlobalIds:
    def test_both_records_are_kept_and_lookup_is_ambiguous(self, tmp_path: Path) -> None:
        path = write_variant(tmp_path, "dup.ifc", duplicate_w002_as_w001)
        index = build_index(open_ifc(path), model_hash="0" * 64)
        shared = GLOBAL_IDS["W-001"]
        assert len(index.of_type("IfcWall")) == 3
        assert list(index.duplicate_global_ids) == [shared]
        express_ids = index.duplicate_global_ids[shared]
        assert len(express_ids) == 2
        assert {index.by_express_id(i).ref.name for i in express_ids} == {"W-001", "W-002"}
        with pytest.raises(AmbiguousGlobalIdError, match=shared):
            index.by_global_id(shared)
        assert index.express_ids_for(shared) == express_ids
        assert index.by_global_id(GLOBAL_IDS["W-003"]).ref.name == "W-003"


class TestMalformedGlobalIds:
    def test_malformed_id_is_recorded_and_the_record_survives(self, tmp_path: Path) -> None:
        path = write_variant(tmp_path, "malformed.ifc", malform_w003)
        index = build_index(open_ifc(path), model_hash="0" * 64)
        w003 = next(r for r in index.of_type("IfcWall") if r.ref.name == "W-003")
        assert w003.ref.global_id is None
        assert w003.ref.key == f"#{w003.ref.express_id}"
        assert index.malformed_global_ids == {w003.ref.express_id: "not-a-valid-guid"}
        assert index.summary.counts["IfcWall"] == 3


class TestTypeInheritance:
    @pytest.fixture
    def typed(self, tmp_path: Path) -> tuple[ModelIndex, ifcopenshell.file]:
        path = write_variant(tmp_path, "typed.ifc", add_wall_type_with_inherited_properties)
        model = open_ifc(path)
        return build_index(model, model_hash="0" * 64), model

    def test_type_object_is_indexed_and_counted(
        self, typed: tuple[ModelIndex, ifcopenshell.file]
    ) -> None:
        index, _ = typed
        types = index.of_type("IfcWallType")
        assert [t.ref.name for t in types] == ["WT-01"]
        assert index.summary.counts["IfcWallType"] == 1
        assert types[0].type_ref is None
        assert types[0].psets["Pset_WallCommon"]["FireRating"].inherited is False

    def test_instance_properties_win_and_inherited_ones_are_flagged(
        self, typed: tuple[ModelIndex, ifcopenshell.file]
    ) -> None:
        index, model = typed
        w001 = index.by_global_id(GLOBAL_IDS["W-001"])
        w002 = index.by_global_id(GLOBAL_IDS["W-002"])
        w003 = index.by_global_id(GLOBAL_IDS["W-003"])
        assert w001.type_ref is not None and w001.type_ref.name == "WT-01"
        assert w003.type_ref is None

        common_1 = w001.psets["Pset_WallCommon"]
        assert (
            common_1["FireRating"].value == "REI 60" and common_1["FireRating"].inherited is False
        )
        assert common_1["LoadBearing"].value is True and common_1["LoadBearing"].inherited is True
        assert common_1["IsExternal"].inherited is False

        common_2 = w002.psets["Pset_WallCommon"]
        assert common_2["FireRating"].value == "REI 120"
        assert common_2["FireRating"].inherited is True
        assert common_2["IsExternal"].inherited is False

        for wall in model.by_type("IfcWall"):
            record = index.by_global_id(wall.GlobalId)
            assert record.plain_psets() == _strip_ids(ifcopenshell.util.element.get_psets(wall))

    def test_classification_inheritance_matches_ifcopenshell(
        self, typed: tuple[ModelIndex, ifcopenshell.file]
    ) -> None:
        index, model = typed
        for wall in model.by_type("IfcWall"):
            record = index.by_global_id(wall.GlobalId)
            expected = {
                ref.Identification for ref in ifcopenshell.util.classification.get_references(wall)
            }
            assert {c.identification for c in record.classifications} == expected, wall.Name
        # W-001 overrides the type's Uniclass reference; W-002 inherits it.
        w001 = index.by_global_id(GLOBAL_IDS["W-001"]).classifications
        assert [(c.identification, c.inherited) for c in w001] == [("Ss_25_10_30", False)]
        w002 = index.by_global_id(GLOBAL_IDS["W-002"]).classifications
        assert [(c.identification, c.inherited) for c in w002] == [("Ss_25_10_30", False)]
        w003 = index.by_global_id(GLOBAL_IDS["W-003"]).classifications
        assert w003 == []


class TestIfc2x3:
    def test_legacy_schema_indexes_with_item_reference(self, ifc2x3_path: Path) -> None:
        index = build_index(open_ifc(ifc2x3_path), model_hash="0" * 64)
        assert index.summary.ifc_schema == "IFC2X3"
        assert index.summary.project_name == "Legacy"
        assert [s.name for s in index.summary.storeys] == ["G"]
        wall_ = index.of_type("IfcWall")[0]
        assert wall_.ref.storey == "G"
        assert wall_.psets["Pset_WallCommon"]["IsExternal"].value is True
        assert [(c.system, c.identification) for c in wall_.classifications] == [
            ("Uniclass 2015", "Ss_25_10_30")
        ]


class TestSerialisation:
    def test_index_round_trips_through_json(self, index: ModelIndex) -> None:
        payload = index.model_dump(mode="json")
        restored = ModelIndex.model_validate(payload)
        assert restored == index
        assert restored.by_global_id(GLOBAL_IDS["W-001"]).ref.name == "W-001"

    def test_index_is_deterministic(self, model: ifcopenshell.file) -> None:
        a = build_index(model, model_hash=MODEL_HASH).model_dump(mode="json")
        b = build_index(open_ifc(IFC_PATH), model_hash=MODEL_HASH).model_dump(mode="json")
        assert a == b

    def test_index_is_immutable(self, index: ModelIndex) -> None:
        with pytest.raises(Exception):  # noqa: B017 - pydantic raises ValidationError
            index.summary = index.summary  # type: ignore[misc]
        assert isinstance(index.summary.storeys[0], ElementRef)


def _strip_ids(psets: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    return {
        name: {key: value for key, value in props.items() if key != "id"}
        for name, props in psets.items()
    }
