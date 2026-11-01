"""FED-001 focused correctness tests on synthetic geometry with independently known relations."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from feasibility.coordination import (
    ARC_FILE,
    DEFAULT_CONFIG,
    ELEMENT_SPECS,
    MEP_FILE,
    REPO_ROOT,
    GeoReference,
    LoadedModel,
    analytic_expectations,
    build_manifest,
    build_model,
    generate_fixtures,
    load_model,
    run_clash,
    run_feasibility,
    run_viewer_probe,
    spec_aabb,
    write_model,
)

ModelSet = tuple[dict[str, Any], list[LoadedModel]]


def _model_set(directory: Path, *, stale: bool = False, **mep_options: Any) -> ModelSet:
    arc_path, mep_path = directory / ARC_FILE, directory / MEP_FILE
    arc_hash = write_model(arc_path, build_model("ARC"))
    mep_hash = write_model(mep_path, build_model("MEP", **mep_options))
    manifest = build_manifest(
        [
            ("ARC", "architecture", arc_path, arc_hash),
            ("MEP", "building_services", mep_path, "0" * 64 if stale else mep_hash),
        ]
    )
    models = [
        load_model("ARC", "architecture", arc_path),
        load_model("MEP", "building_services", mep_path),
    ]
    return manifest, models


def _pairs(result: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(item["a"]["name"], item["b"]["name"]): item for item in result["intersections"]}


@pytest.fixture(scope="module")
def baseline(tmp_path_factory: pytest.TempPathFactory) -> tuple[ModelSet, dict[str, Any]]:
    model_set = _model_set(tmp_path_factory.mktemp("fed001"))
    result, _ = run_clash(model_set[1], model_set[0])
    return model_set, result


def test_fixture_generation_is_byte_deterministic(tmp_path: Path) -> None:
    first = [path.read_bytes() for path in generate_fixtures(tmp_path / "one")]
    second = [path.read_bytes() for path in generate_fixtures(tmp_path / "two")]
    assert first == second


def test_profiles_record_frame_facts(baseline: tuple[ModelSet, dict[str, Any]]) -> None:
    (_, models), _ = baseline
    for model in models:
        profile = model.profile
        assert profile["schema"] == "IFC4"
        assert profile["units"] == {"length_unit": "METRE", "si_scale": 1.0}
        assert len(profile["coordinate_reference"]["map_conversions"]) == 1
        assert profile["geometry"]["status"] in {"loaded", "partial"}
        boxes = [
            spec_aabb(spec)
            for spec in ELEMENT_SPECS[model.member_id]
            if spec.has_body and spec.ifc_class != "IfcSpace"
        ]
        expected_min = [min(box[0][i] for box in boxes) for i in range(3)]
        expected_max = [max(box[1][i] for box in boxes) for i in range(3)]
        assert profile["world_bbox_m"]["min"] == pytest.approx(expected_min, abs=1e-6)
        assert profile["world_bbox_m"]["max"] == pytest.approx(expected_max, abs=1e-6)
    sites = [m.profile["coordinate_reference"]["site_placement_matrix"] for m in models]
    assert sites[0] != sites[1], "fixture must exercise differing IfcSite placements"


def test_alignment_accepts_shared_frame(baseline: tuple[ModelSet, dict[str, Any]]) -> None:
    _, result = baseline
    assert result["alignment"]["status"] == "aligned"
    assert result["alignment"]["reasons"] == []
    assert result["alignment"]["transform"] == "identity"


def test_known_through_penetration_is_hard(baseline: tuple[ModelSet, dict[str, Any]]) -> None:
    _, result = baseline
    record = _pairs(result)[("W-A01", "D-B01")]
    assert record["classification"] == "hard_intersection"
    assert record["status"] == "raw_geometric_result"
    assert record["professional_action"] == "not_assessed"
    assert record["aabb_overlap_m"] == {"min": [102.0, 50.0, 1.5], "max": [102.4, 50.2, 1.9]}


def test_separated_control_is_absent(baseline: tuple[ModelSet, dict[str, Any]]) -> None:
    _, result = baseline
    assert all(a != "W-A02" and b != "P-B02" for a, b in _pairs(result))


def test_tolerance_boundary(baseline: tuple[ModelSet, dict[str, Any]]) -> None:
    _, result = baseline
    pairs = _pairs(result)
    within = pairs[("W-A03", "D-B02")]
    beyond = pairs[("W-A03", "D-B03")]
    assert (within["classification"], within["detail"]) == (
        "touch_contact",
        "overlap_not_exceeding_tolerance",
    )
    assert beyond["classification"] == "hard_intersection"
    assert beyond["cross_check"]["engine_penetration_distance_m"] == pytest.approx(0.005, abs=1e-6)


def test_surface_contact_is_touch(baseline: tuple[ModelSet, dict[str, Any]]) -> None:
    _, result = baseline
    record = _pairs(result)[("SL-A01", "P-B01")]
    assert (record["classification"], record["detail"]) == ("touch_contact", "surface_contact")


def test_results_match_independent_box_oracle(baseline: tuple[ModelSet, dict[str, Any]]) -> None:
    _, result = baseline
    observed = {pair: item["classification"] for pair, item in _pairs(result).items()}
    expected = {
        pair: value["relation"]
        for pair, value in analytic_expectations().items()
        if value["relation"] != "separated"
    }
    assert observed == expected
    assert result["summary"]["unique_intersecting_pairs"] == 5
    assert result["summary"]["hard_intersections"] == 3
    assert result["summary"]["unsupported_engine_disagreements"] == 0
    assert result["state"] == "results_available"


def test_coplanar_embedded_overlap_is_hard(baseline: tuple[ModelSet, dict[str, Any]]) -> None:
    """Regression: an overlap sharing both face planes must be classified hard."""
    _, result = baseline
    record = _pairs(result)[("W-A05", "D-B04")]
    assert record["classification"] == "hard_intersection"
    assert set(record["cross_check"]) >= {"engine", "classification", "agrees"}


def test_every_record_identifies_source_model_and_element(
    baseline: tuple[ModelSet, dict[str, Any]],
) -> None:
    (_, models), result = baseline
    hashes = {model.member_id: model.sha256 for model in models}
    for record in result["intersections"]:
        assert record["a"]["member_id"] == "ARC" and record["b"]["member_id"] == "MEP"
        for side in (record["a"], record["b"]):
            assert side["model_sha256"] == hashes[side["member_id"]]
            assert side["global_id"]
            assert side["element_key"] == (
                f"{side['member_id']}|{side['model_sha256']}|{side['global_id']}"
            )


def test_duplicate_global_id_across_models_is_distinguished(
    baseline: tuple[ModelSet, dict[str, Any]],
) -> None:
    _, result = baseline
    record = _pairs(result)[("W-A01", "D-B01")]
    assert record["a"]["global_id"] == record["b"]["global_id"]
    assert record["a"]["element_key"] != record["b"]["element_key"]


def test_unsupported_element_is_skipped(baseline: tuple[ModelSet, dict[str, Any]]) -> None:
    _, result = baseline
    assert [(s["element"]["name"], s["reason"]) for s in result["skipped"]] == [
        ("W-A04", "no_representation")
    ]
    assert all(s["classification"] == "unsupported" for s in result["skipped"])


def test_excluded_and_out_of_scope_classes(baseline: tuple[ModelSet, dict[str, Any]]) -> None:
    _, result = baseline
    assert [item["element"]["name"] for item in result["excluded"]] == ["SP-A01"]
    names = {name for pair in _pairs(result) for name in pair}
    assert "SP-A01" not in names and "PX-A01" not in names


def test_configured_exclusion_removes_a_real_overlap(
    baseline: tuple[ModelSet, dict[str, Any]],
) -> None:
    (manifest, models), _ = baseline
    broad = {**DEFAULT_CONFIG, "include_a": ["IfcBuildingElement"]}
    included, _ = run_clash(models, manifest, broad)
    assert _pairs(included)[("PX-A01", "D-B01")]["classification"] == "hard_intersection"
    proxy_rule = {"ifc_class": "IfcBuildingElementProxy", "reason": "Intentional placeholder."}
    excluded_config = {**broad, "exclusions": [*DEFAULT_CONFIG["exclusions"], proxy_rule]}
    excluded, _ = run_clash(models, manifest, excluded_config)
    assert ("PX-A01", "D-B01") not in _pairs(excluded)
    assert "PX-A01" in [item["element"]["name"] for item in excluded["excluded"]]


def test_swapped_pair_is_attributed_to_source_models(
    baseline: tuple[ModelSet, dict[str, Any]],
) -> None:
    (manifest, models), result = baseline
    swapped_config = {
        **DEFAULT_CONFIG,
        "pair": {"a": "MEP", "b": "ARC"},
        "include_a": DEFAULT_CONFIG["include_b"],
        "include_b": DEFAULT_CONFIG["include_a"],
    }
    swapped, _ = run_clash(models, manifest, swapped_config)
    original = {(b, a): item["classification"] for (a, b), item in _pairs(result).items()}
    assert {pair: item["classification"] for pair, item in _pairs(swapped).items()} == original
    assert all(item["a"]["member_id"] == "MEP" for item in swapped["intersections"])


def test_rerun_from_fresh_parse_is_identical(
    baseline: tuple[ModelSet, dict[str, Any]],
) -> None:
    (manifest, models), result = baseline
    reloaded = [load_model(m.member_id, m.discipline, m.path) for m in models]
    again, timings = run_clash(reloaded, manifest)
    assert again["result_digest"] == result["result_digest"]
    assert "exact_query_seconds" in timings and "seconds" not in str(sorted(result))


def test_malformed_placement_is_skipped_not_compared(tmp_path: Path) -> None:
    manifest, models = _model_set(tmp_path, malformed_labels=frozenset({"D-B03"}))
    result, _ = run_clash(models, manifest)
    assert result["alignment"]["status"] == "aligned"
    assert ("D-B03", "malformed_placement") in [
        (s["element"]["name"], s["reason"]) for s in result["skipped"]
    ]
    assert ("W-A03", "D-B03") not in _pairs(result)
    assert ("W-A01", "D-B01") in _pairs(result)


@pytest.mark.parametrize(
    ("options", "code"),
    [
        ({"georeferences": ()}, "missing_georeference"),
        ({"georeferences": (GeoReference(eastings=530010.0),)}, "mismatched_georeference"),
        ({"georeferences": (GeoReference(crs_name="EPSG:3857"),)}, "mismatched_georeference"),
        ({"georeferences": (GeoReference(), GeoReference())}, "ambiguous_georeference"),
        ({"length_unit": "MILLIMETERS"}, "unit_mismatch"),
        ({"stale": True}, "stale_model_hash"),
    ],
)
def test_alignment_gate_fails_closed(tmp_path: Path, options: dict[str, Any], code: str) -> None:
    manifest, models = _model_set(tmp_path, **options)
    result, timings = run_clash(models, manifest)
    assert result["alignment"]["status"] == "rejected"
    assert code in [reason["code"] for reason in result["alignment"]["reasons"]]
    assert result["state"] == "not_analysed"
    assert result["intersections"] == []
    assert timings == {}


def _viewer_available() -> bool:
    return (
        shutil.which("node") is not None
        and (REPO_ROOT / "frontend" / "node_modules" / "web-ifc").is_dir()
    )


@pytest.mark.skipif(not _viewer_available(), reason="node or frontend web-ifc not installed")
def test_viewer_probe_places_both_models_in_one_frame(
    baseline: tuple[ModelSet, dict[str, Any]],
) -> None:
    (_, models), _ = baseline
    probe = run_viewer_probe(models)
    assert probe["status"] == "consistent", probe
    assert probe["web_ifc_version"] == "0.0.77"
    assert probe["compared_elements"] == sum(len(m.world_aabbs) for m in models)
    assert probe["models"][0]["fragments_translation"] == [0.0, 0.0, 0.0]


@pytest.mark.skipif(not _viewer_available(), reason="node or frontend web-ifc not installed")
def test_end_to_end_feasibility_decision(tmp_path: Path) -> None:
    report = run_feasibility(tmp_path / "fixtures", tmp_path / "reports")
    assert report["go_no_go"]["decision"] == "GO", report["go_no_go"]
    assert report["private_models_accessed"] is False
    assert (tmp_path / "reports" / "coordination-feasibility.json").is_file()
    assert (tmp_path / "reports" / "fed001-clash-result.json").is_file()
