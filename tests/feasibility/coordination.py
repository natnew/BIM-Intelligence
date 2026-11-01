"""FED-001: two-model IFC federation and deterministic clash feasibility.

This is an isolated engineering experiment. It generates a synthetic architectural (ARC) and
building-services (MEP) IFC pair with independently known geometry, verifies that both models
share one coordinate reference frame, runs one explicit A/B clash comparison with the installed
IfcOpenShell geometry tree, and checks that the existing That Open browser path would place both
models consistently. Nothing here is imported by the application.

Raw geometric intersections are not coordination issues: every result is a deterministic
geometric fact that still needs professional triage.

Run from the repository root:

    python -c "import sys; sys.path.insert(0, 'tests'); \
from feasibility.coordination import main; raise SystemExit(main())"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit
import ifcopenshell.geom
import ifcopenshell.guid
import ifcopenshell.util.placement
import ifcopenshell.util.unit
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_DIR = REPO_ROOT / "datasets" / "synthetic" / "generated" / "fed001"
DEFAULT_REPORT_DIR = REPO_ROOT / "local-private" / "test-results" / "final-48h"
VIEWER_PROBE = Path(__file__).resolve().parent / "webifc_viewer_probe.mjs"

RESULT_SCHEMA = "fed001.clash-result.v1"
MANIFEST_SCHEMA = "fed001.model-set.v1"
REPORT_SCHEMA = "fed001.coordination-feasibility.v1"
MODEL_SET_ID = "fed001-synthetic-arc-mep"
ARC_FILE = "fed001-arc.ifc"
MEP_FILE = "fed001-mep.ifc"
MANIFEST_FILE = "fed001-model-set.json"

GEOMETRY_LIBRARY: Final = "opencascade"
PRIMARY_ENGINE = "opencascade.brep"
CROSS_CHECK_ENGINE = "opencascade.trianglebvh"
COORDINATE_DECIMALS = 6
FRAME_TOLERANCE = 1e-9
VIEWER_TOLERANCE_M = 1e-4
ENGINE_CLASH_TYPES = {0: "protrusion", 1: "pierce", 2: "collision", 3: "clearance"}

_GUID_NAMESPACE = uuid.UUID("5d0f6f55-0f0b-4c55-9a52-fed001000000")
_FIXED_TIMESTAMP = "2026-11-01T00:00:00"
# Shared project engineering origin; deliberately away from (0, 0, 0).
PROJECT_OFFSET = (100.0, 50.0, 0.0)
# Different IfcSite placements per discipline: element world coordinates, not site placement,
# are what the shared IfcMapConversion maps from.
SITE_ORIGINS = {"ARC": (100.0, 50.0, 0.0), "MEP": (0.0, 0.0, 0.0)}

Vec3 = tuple[float, float, float]
Aabb = tuple[Vec3, Vec3]


class FeasibilityError(RuntimeError):
    """Raised when the FED-001 experiment cannot proceed with trustworthy inputs."""


@dataclass(frozen=True)
class GeoReference:
    crs_name: str = "EPSG:27700"
    eastings: float = 530000.0
    northings: float = 180000.0
    orthogonal_height: float = 0.0
    x_axis_abscissa: float = 1.0
    x_axis_ordinate: float = 0.0
    scale: float = 1.0


DEFAULT_GEOREFERENCE = GeoReference()


@dataclass(frozen=True)
class ElementSpec:
    """An axis-aligned box in the shared project frame, relative to ``PROJECT_OFFSET``."""

    label: str
    ifc_class: str
    origin: Vec3
    size: Vec3
    has_body: bool = True
    global_id_label: str | None = None
    purpose: str = ""


ELEMENT_SPECS: dict[str, tuple[ElementSpec, ...]] = {
    "ARC": (
        ElementSpec("W-A01", "IfcWall", (0.0, 0.0, 0.0), (6.0, 0.2, 3.0), purpose="hard target"),
        ElementSpec(
            "W-A02", "IfcWall", (0.0, 10.0, 0.0), (6.0, 0.2, 3.0), purpose="separated control"
        ),
        ElementSpec("SL-A01", "IfcSlab", (10.0, 0.0, 0.0), (4.0, 4.0, 0.2), purpose="contact"),
        ElementSpec(
            "W-A03", "IfcWall", (20.0, 0.0, 0.0), (4.0, 0.2, 3.0), purpose="tolerance boundary"
        ),
        ElementSpec(
            "SP-A01", "IfcSpace", (1.5, -1.0, 0.0), (2.0, 3.0, 3.0), purpose="excluded class"
        ),
        ElementSpec(
            "W-A04",
            "IfcWall",
            (30.0, 0.0, 0.0),
            (4.0, 0.2, 3.0),
            has_body=False,
            purpose="unsupported: no representation",
        ),
        ElementSpec(
            "PX-A01",
            "IfcBuildingElementProxy",
            (2.0, -0.5, 1.5),
            (0.4, 1.2, 0.4),
            purpose="out of scope; exactly coincides with D-B01",
        ),
        ElementSpec(
            "W-A05", "IfcWall", (40.0, 0.0, 0.0), (4.0, 0.2, 3.0), purpose="coplanar overlap"
        ),
    ),
    "MEP": (
        ElementSpec(
            "D-B01",
            "IfcDuctSegment",
            (2.0, -0.5, 1.5),
            (0.4, 1.2, 0.4),
            global_id_label="ARC:W-A01",
            purpose="through-penetration; duplicates W-A01 GlobalId",
        ),
        ElementSpec(
            "P-B01", "IfcPipeSegment", (11.0, 1.0, 0.2), (1.0, 0.1, 0.1), purpose="rests on slab"
        ),
        ElementSpec(
            "D-B02",
            "IfcDuctSegment",
            (21.0, 0.199, 1.0),
            (0.4, 0.5, 0.4),
            purpose="1 mm overlap (within tolerance)",
        ),
        ElementSpec(
            "D-B03",
            "IfcDuctSegment",
            (22.5, -0.495, 1.0),
            (0.4, 0.5, 0.4),
            purpose="5 mm overlap (exceeds tolerance)",
        ),
        ElementSpec(
            "P-B02",
            "IfcPipeSegment",
            (0.0, 10.25, 1.0),
            (1.0, 0.1, 0.1),
            purpose="50 mm clear of W-A02 (must be absent)",
        ),
        ElementSpec(
            "D-B04",
            "IfcDuctSegment",
            (41.0, 0.0, 1.0),
            (0.4, 0.2, 0.4),
            purpose="embedded flush in W-A05; shares both wall face planes",
        ),
    ),
}

DEFAULT_CONFIG: dict[str, Any] = {
    "pair": {"a": "ARC", "b": "MEP"},
    "include_a": ["IfcWall", "IfcSlab"],
    "include_b": ["IfcDuctSegment", "IfcPipeSegment"],
    "exclusions": [
        {"ifc_class": "IfcSpace", "reason": "Spaces intentionally overlap building elements."},
        {"ifc_class": "IfcOpeningElement", "reason": "Openings are subtraction features."},
    ],
    "tolerance_m": 0.002,
    "contact_epsilon_m": 1e-6,
    "collision_types": ["hard_intersection", "touch_contact"],
    "geometry_library": GEOMETRY_LIBRARY,
    "primary_engine": PRIMARY_ENGINE,
    "cross_check_engine": CROSS_CHECK_ENGINE,
    "coordinate_decimals": COORDINATE_DECIMALS,
    "placement_assumption": (
        "Element world coordinates from IfcLocalPlacement chains are in one shared project "
        "engineering CRS, verified by identical IfcMapConversion, units and context frame."
    ),
}

SEMANTICS = (
    "Each record is a raw geometric relationship between two source elements. It is not a "
    "coordination issue: professional triage decides whether action is required."
)


@dataclass
class LoadedModel:
    member_id: str
    discipline: str
    path: Path
    sha256: str
    file: Any
    shapes: dict[int, Any] = field(default_factory=dict)
    world_aabbs: dict[int, Aabb] = field(default_factory=dict)
    geometry_failures: dict[int, str] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)
    iterator: Any = None


# ---------------------------------------------------------------------------------------------
# Synthetic fixtures


def deterministic_guid(label: str) -> str:
    return str(ifcopenshell.guid.compress(uuid.uuid5(_GUID_NAMESPACE, label).hex))


def build_model(
    discipline: str,
    *,
    georeferences: Sequence[GeoReference] = (DEFAULT_GEOREFERENCE,),
    length_unit: str = "METERS",
    malformed_labels: frozenset[str] = frozenset(),
) -> Any:
    """Build one synthetic discipline model. Variants are built fresh, never edited in place."""
    if discipline not in ELEMENT_SPECS:
        raise FeasibilityError(f"Unknown discipline {discipline!r}.")
    model = ifcopenshell.api.project.create_file(version="IFC4")
    model.header.file_description.description = ("ViewDefinition[ReferenceView]",)
    model.header.file_name.name = f"fed001-{discipline.lower()}.ifc"
    model.header.file_name.time_stamp = _FIXED_TIMESTAMP
    model.header.file_name.author = ("BIM Intelligence FED-001 synthetic fixture",)
    model.header.file_name.organization = ("natnew/BIM-Intelligence",)
    model.header.file_name.preprocessor_version = "tests/feasibility/coordination.py"
    model.header.file_name.originating_system = "BIM Intelligence"
    model.header.file_name.authorization = "none"

    project = _create(model, "IfcProject", f"FED-001 {discipline}")
    ifcopenshell.api.unit.assign_unit(model, length={"is_metric": True, "raw": length_unit})
    model_context = ifcopenshell.api.context.add_context(model, context_type="Model")
    body = ifcopenshell.api.context.add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )
    for georeference in georeferences:
        _add_map_conversion(model, model_context, georeference)

    site = _create(model, "IfcSite", f"{discipline} Site")
    building = _create(model, "IfcBuilding", f"{discipline} Building")
    storey = _create(model, "IfcBuildingStorey", "L00")
    ifcopenshell.api.aggregate.assign_object(model, products=[site], relating_object=project)
    ifcopenshell.api.aggregate.assign_object(model, products=[building], relating_object=site)
    ifcopenshell.api.aggregate.assign_object(model, products=[storey], relating_object=building)
    site_origin = SITE_ORIGINS[discipline]
    for spatial in (site, building, storey):
        _set_placement(model, spatial, site_origin)

    for spec in ELEMENT_SPECS[discipline]:
        product = _create(model, spec.ifc_class, spec.label)
        if spec.ifc_class == "IfcSpace":
            ifcopenshell.api.aggregate.assign_object(
                model, products=[product], relating_object=storey
            )
        else:
            ifcopenshell.api.spatial.assign_container(
                model, products=[product], relating_structure=storey
            )
        _set_placement(model, product, world_origin(spec))
        if spec.has_body:
            representation = ifcopenshell.api.geometry.add_wall_representation(
                model,
                context=body,
                length=spec.size[0],
                thickness=spec.size[1],
                height=spec.size[2],
            )
            ifcopenshell.api.geometry.assign_representation(
                model, product=product, representation=representation
            )
        if spec.label in malformed_labels:
            relative = product.ObjectPlacement.RelativePlacement
            relative.Axis = model.createIfcDirection((0.0, 0.0, 0.0))
            relative.RefDirection = model.createIfcDirection((0.0, 0.0, 0.0))

    labels = {spec.label: spec for spec in ELEMENT_SPECS[discipline]}
    for index, root in enumerate(model.by_type("IfcRoot")):
        name = getattr(root, "Name", None) or ""
        root_spec = labels.get(name)
        if root_spec is not None:
            root.GlobalId = deterministic_guid(root_spec.global_id_label or f"{discipline}:{name}")
        else:
            root.GlobalId = deterministic_guid(f"{discipline}:root:{index}:{root.is_a()}:{name}")
    _canonicalise_sets(model)
    return model


def _canonicalise_sets(model: Any) -> None:
    """Sort unordered SET/BAG entity aggregates so serialisation is byte-stable."""
    wrapper: Any = ifcopenshell.ifcopenshell_wrapper
    unordered = {wrapper.aggregation_type.set_type, wrapper.aggregation_type.bag_type}
    schema: Any = wrapper.schema_by_name(model.schema_identifier)
    for entity in model:
        declaration = schema.declaration_by_name(entity.is_a())
        derived = declaration.derived()
        for index, attribute in enumerate(declaration.all_attributes()):
            kind = attribute.type_of_attribute()
            if derived[index] or not isinstance(kind, wrapper.aggregation_type):
                continue
            if kind.type_of_aggregation() not in unordered:
                continue
            value = entity[index]
            if (
                isinstance(value, tuple)
                and value
                and all(isinstance(item, ifcopenshell.entity_instance) for item in value)
            ):
                entity[index] = tuple(sorted(value, key=lambda item: item.id()))


def world_origin(spec: ElementSpec) -> Vec3:
    return (
        PROJECT_OFFSET[0] + spec.origin[0],
        PROJECT_OFFSET[1] + spec.origin[1],
        PROJECT_OFFSET[2] + spec.origin[2],
    )


def spec_aabb(spec: ElementSpec) -> Aabb:
    low = world_origin(spec)
    high = (low[0] + spec.size[0], low[1] + spec.size[1], low[2] + spec.size[2])
    return low, high


def write_model(path: Path, model: Any) -> str:
    data = model.to_string().replace("\r\n", "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def build_manifest(
    members: Sequence[tuple[str, str, Path, str]],
    georeference: GeoReference = DEFAULT_GEOREFERENCE,
) -> dict[str, Any]:
    """Model-set manifest: ``members`` holds ``(member_id, discipline, path, sha256)``."""
    return {
        "schema": MANIFEST_SCHEMA,
        "model_set_id": MODEL_SET_ID,
        "data_class": "synthetic",
        "common_frame": {
            "kind": "shared_project_engineering_crs",
            "projected_crs": georeference.crs_name,
            "map_conversion": _georeference_record(georeference),
            "length_unit": "METRE",
            "transform": "identity",
        },
        "members": [
            {
                "member_id": member_id,
                "discipline": discipline,
                "file": path.name,
                "sha256": sha256,
                "schema": "IFC4",
            }
            for member_id, discipline, path, sha256 in members
        ],
    }


def generate_fixtures(output_dir: Path = DEFAULT_FIXTURE_DIR) -> tuple[Path, Path, Path]:
    """Write the baseline ARC/MEP pair and its manifest; returns ``(arc, mep, manifest)``."""
    arc_path = output_dir / ARC_FILE
    mep_path = output_dir / MEP_FILE
    arc_hash = write_model(arc_path, build_model("ARC"))
    mep_hash = write_model(mep_path, build_model("MEP"))
    manifest = build_manifest(
        [
            ("ARC", "architecture", arc_path, arc_hash),
            ("MEP", "building_services", mep_path, mep_hash),
        ]
    )
    manifest_path = output_dir / MANIFEST_FILE
    manifest_path.write_bytes(_json_bytes(manifest))
    return arc_path, mep_path, manifest_path


def analytic_expectations(
    config: Mapping[str, Any] = DEFAULT_CONFIG,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Independent oracle from box arithmetic: expected relation for every in-scope A/B pair."""
    tolerance = float(config["tolerance_m"])
    expectations: dict[tuple[str, str], dict[str, Any]] = {}
    for spec_a in _in_scope_specs("ARC", config["include_a"], config["exclusions"]):
        for spec_b in _in_scope_specs("MEP", config["include_b"], config["exclusions"]):
            low_a, high_a = spec_aabb(spec_a)
            low_b, high_b = spec_aabb(spec_b)
            depth = min(min(high_a[i], high_b[i]) - max(low_a[i], low_b[i]) for i in range(3))
            if depth > tolerance + FRAME_TOLERANCE:
                relation = "hard_intersection"
            elif depth >= -FRAME_TOLERANCE:
                relation = "touch_contact"
            else:
                relation = "separated"
            expectations[(spec_a.label, spec_b.label)] = {
                "relation": relation,
                "depth_m": round(depth, COORDINATE_DECIMALS),
            }
    return expectations


# ---------------------------------------------------------------------------------------------
# Loading and profiling


def load_model(member_id: str, discipline: str, path: Path) -> LoadedModel:
    data = path.read_bytes()
    started = time.perf_counter()
    try:
        ifc = ifcopenshell.open(str(path))
    except Exception as error:
        raise FeasibilityError(f"{member_id}: IFC parse failed: {error}") from error
    loaded = LoadedModel(
        member_id=member_id,
        discipline=discipline,
        path=path,
        sha256=hashlib.sha256(data).hexdigest(),
        file=ifc,
    )
    loaded.timings["parse_seconds"] = time.perf_counter() - started

    started = time.perf_counter()
    geometry_status = _load_geometry(loaded)
    loaded.timings["geometry_seconds"] = time.perf_counter() - started
    loaded.profile = _profile(loaded, geometry_status, len(data))
    return loaded


def placement_problem(product: Any) -> str | None:
    if product.ObjectPlacement is None:
        return "missing_placement"
    with np.errstate(all="ignore"):
        try:
            matrix = np.asarray(
                ifcopenshell.util.placement.get_local_placement(product.ObjectPlacement)
            )
        except Exception:
            return "malformed_placement"
        if matrix.shape != (4, 4) or not np.all(np.isfinite(matrix)):
            return "malformed_placement"
        rotation = matrix[:3, :3]
        if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6):
            return "malformed_placement"
        if np.linalg.det(rotation) <= 0:
            return "malformed_placement"
    return None


def _load_geometry(loaded: LoadedModel) -> str:
    candidates: list[Any] = []
    for element in sorted(loaded.file.by_type("IfcElement"), key=lambda item: item.id()):
        if element.is_a("IfcFeatureElement"):
            continue
        if element.Representation is None:
            loaded.geometry_failures[element.id()] = "no_representation"
            continue
        problem = placement_problem(element)
        if problem is not None:
            loaded.geometry_failures[element.id()] = problem
            continue
        candidates.append(element)
    if not candidates:
        return "no_geometry"

    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    try:
        iterator = ifcopenshell.geom.iterator(
            settings, loaded.file, 1, include=candidates, geometry_library=GEOMETRY_LIBRARY
        )
        initialised = iterator.initialize()
    except Exception as error:
        for element in candidates:
            loaded.geometry_failures[element.id()] = f"geometry_error: {error}"
        return "failed"
    if initialised:
        while True:
            shape = iterator.get()
            vertices = np.asarray(shape.geometry.verts, dtype=float).reshape(-1, 3)
            if len(vertices):
                loaded.shapes[shape.id] = shape
                loaded.world_aabbs[shape.id] = (
                    _vec(vertices.min(axis=0)),
                    _vec(vertices.max(axis=0)),
                )
            if not iterator.next():
                break
    loaded.iterator = iterator
    for element in candidates:
        if element.id() not in loaded.shapes:
            loaded.geometry_failures[element.id()] = "geometry_not_produced"
    if not loaded.shapes:
        return "failed"
    return "loaded" if not loaded.geometry_failures else "partial"


def _profile(loaded: LoadedModel, geometry_status: str, size_bytes: int) -> dict[str, Any]:
    ifc = loaded.file
    length_unit = ifcopenshell.util.unit.get_project_unit(ifc, "LENGTHUNIT")
    unit_name = None
    if length_unit is not None:
        prefix = getattr(length_unit, "Prefix", None) or ""
        unit_name = f"{prefix}{length_unit.Name}"
    counts: dict[str, int] = {}
    for product in ifc.by_type("IfcProduct"):
        counts[product.is_a()] = counts.get(product.is_a(), 0) + 1
    failures: dict[str, int] = {}
    for reason in loaded.geometry_failures.values():
        failures[reason] = failures.get(reason, 0) + 1
    bbox = _union_aabb(loaded.world_aabbs.values())
    sites = ifc.by_type("IfcSite")
    site_placement = None
    if len(sites) == 1 and placement_problem(sites[0]) is None:
        matrix = np.asarray(
            ifcopenshell.util.placement.get_local_placement(sites[0].ObjectPlacement)
        )
        site_placement = _round_nested(matrix.tolist())
    return {
        "member_id": loaded.member_id,
        "discipline": loaded.discipline,
        "file": loaded.path.name,
        "sha256": loaded.sha256,
        "size_bytes": size_bytes,
        "schema": ifc.schema_identifier,
        "units": {
            "length_unit": unit_name,
            "si_scale": ifcopenshell.util.unit.calculate_unit_scale(ifc),
        },
        "coordinate_reference": {
            "map_conversions": [_map_conversion_record(item) for item in _map_conversions(ifc)],
            "model_contexts": [_context_record(item) for item in _model_contexts(ifc)],
            "site_placement_matrix": site_placement,
        },
        "geometry": {
            "status": geometry_status,
            "library": GEOMETRY_LIBRARY,
            "produced": len(loaded.shapes),
            "not_produced": failures,
        },
        "world_bbox_m": None if bbox is None else {"min": list(bbox[0]), "max": list(bbox[1])},
        "spatial_extent_m": None
        if bbox is None
        else [round(bbox[1][i] - bbox[0][i], COORDINATE_DECIMALS) for i in range(3)],
        "element_counts": dict(sorted(counts.items())),
    }


# ---------------------------------------------------------------------------------------------
# Federation gate


def assess_alignment(models: Sequence[LoadedModel], manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Accept a common frame only with direct evidence; never infer alignment from extents."""
    reasons: list[dict[str, str]] = []
    members = {member["member_id"]: member for member in manifest.get("members", [])}
    for model in models:
        member = members.get(model.member_id)
        if member is None:
            reasons.append(_reason("unknown_member", model.member_id, "Not in manifest."))
        elif member.get("sha256") != model.sha256:
            reasons.append(
                _reason("stale_model_hash", model.member_id, "File hash differs from manifest.")
            )
        if len(_model_contexts(model.file)) != 1:
            reasons.append(
                _reason("unverifiable_frame", model.member_id, "Expected one 3D Model context.")
            )
        count = len(model.profile["coordinate_reference"]["map_conversions"])
        if count == 0:
            reasons.append(_reason("missing_georeference", model.member_id, "No IfcMapConversion."))
        elif count > 1:
            reasons.append(
                _reason("ambiguous_georeference", model.member_id, f"{count} IfcMapConversions.")
            )

    scales = {model.profile["units"]["si_scale"] for model in models}
    if len(scales) > 1:
        reasons.append(
            _reason("unit_mismatch", "*", f"Length unit scales differ: {sorted(scales)}.")
        )

    conversions = [model.profile["coordinate_reference"]["map_conversions"] for model in models]
    common_frame: dict[str, Any] | None = None
    if all(len(items) == 1 for items in conversions):
        first = conversions[0][0]
        for model, items in zip(models[1:], conversions[1:], strict=True):
            if not _same_record(first, items[0]):
                reasons.append(
                    _reason("mismatched_georeference", model.member_id, "IfcMapConversion differs.")
                )
        expected = manifest.get("common_frame", {}).get("map_conversion")
        if expected is not None and not _same_record(first, expected):
            reasons.append(
                _reason("mismatched_georeference", "*", "Models disagree with manifest frame.")
            )
        common_frame = first

    contexts = [model.profile["coordinate_reference"]["model_contexts"] for model in models]
    if all(len(items) == 1 for items in contexts):
        for model, items in zip(models[1:], contexts[1:], strict=True):
            if not _same_record(contexts[0][0], items[0]):
                reasons.append(
                    _reason(
                        "mismatched_engineering_frame",
                        model.member_id,
                        "WorldCoordinateSystem or TrueNorth differs.",
                    )
                )

    boxes = [_union_aabb(model.world_aabbs.values()) for model in models]
    overlap = None
    if all(box is not None for box in boxes):
        overlap = _aabb_overlap([box for box in boxes if box is not None]) is not None
    return {
        "status": "aligned" if not reasons else "rejected",
        "reasons": sorted(reasons, key=lambda item: (item["code"], item["member_id"])),
        "common_frame": common_frame if not reasons else None,
        "transform": "identity" if not reasons else None,
        "evidence": "identical IfcMapConversion, length unit, model context frame and hashes",
        "extent_overlap_informational_only": overlap,
    }


# ---------------------------------------------------------------------------------------------
# Clash comparison


def run_clash(
    models: Sequence[LoadedModel],
    manifest: Mapping[str, Any],
    config: Mapping[str, Any] = DEFAULT_CONFIG,
) -> tuple[dict[str, Any], dict[str, float]]:
    """Run one A/B comparison. Returns the deterministic result and separate timings."""
    by_member = {model.member_id: model for model in models}
    model_a = by_member[config["pair"]["a"]]
    model_b = by_member[config["pair"]["b"]]
    alignment = assess_alignment([model_a, model_b], manifest)
    timings: dict[str, float] = {}
    errors: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []

    scope_a = _scope(model_a, config["include_a"], config["exclusions"])
    scope_b = _scope(model_b, config["include_b"], config["exclusions"])
    skipped = _skipped(model_a, scope_a["in_scope"]) + _skipped(model_b, scope_b["in_scope"])
    set_a = [item for item in scope_a["in_scope"] if item.id() in model_a.shapes]
    set_b = [item for item in scope_b["in_scope"] if item.id() in model_b.shapes]

    if alignment["status"] != "aligned":
        state = "not_analysed"
    elif not set_a or not set_b:
        state = "not_analysed"
        errors.append({"code": "no_comparable_elements", "detail": "An A or B set is empty."})
    else:
        try:
            records, timings = _compare(model_a, model_b, set_a, set_b, config)
            state = "results_available" if records else "zero_clashes"
        except Exception as error:
            state = "analysis_error"
            errors.append({"code": "clash_engine_error", "detail": str(error)})

    hard = sum(1 for item in records if item["classification"] == "hard_intersection")
    touch = sum(1 for item in records if item["classification"] == "touch_contact")
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "data_class": "synthetic",
        "model_set_id": manifest.get("model_set_id"),
        "engine": {
            "ifcopenshell": ifcopenshell.version,
            "geometry_library": config["geometry_library"],
            "primary": {
                "backend": config["primary_engine"],
                "iterator_output": "NATIVE (exact B-rep)",
                "queries": [
                    "select(a, extend=-tolerance_m) -> hard_intersection",
                    "select(a, extend=0.0) -> overlap_not_exceeding_tolerance",
                    "select(a, extend=contact_epsilon_m) -> surface_contact",
                ],
            },
            "cross_check": {
                "backend": config["cross_check_engine"],
                "queries": [
                    "clash_intersection_many(tolerance=tolerance_m, check_all=True)",
                    "clash_collision_many(allow_touching=True)",
                ],
            },
        },
        "discipline_pair": {
            "a": {"member_id": model_a.member_id, "discipline": model_a.discipline},
            "b": {"member_id": model_b.member_id, "discipline": model_b.discipline},
        },
        "models": [_model_identity(model) for model in (model_a, model_b)],
        "configuration": dict(config),
        "configuration_hash": _digest(dict(config)),
        "input_hash": _digest(
            {"configuration": dict(config), "models": [model_a.sha256, model_b.sha256]}
        ),
        "alignment": alignment,
        "state": state,
        "summary": {
            "unique_intersecting_pairs": len(records),
            "hard_intersections": hard,
            "touch_contacts": touch,
            "unsupported_engine_disagreements": len(records) - hard - touch,
            "cross_check_disagreements": sum(
                1 for item in records if not item["cross_check"]["agrees"]
            ),
            "compared_elements": {"a": len(set_a), "b": len(set_b)},
            "excluded_by_configuration": len(scope_a["excluded"]) + len(scope_b["excluded"]),
            "out_of_scope_elements": scope_a["out_of_scope"] + scope_b["out_of_scope"],
            "skipped_unsupported": len(skipped),
        },
        "intersections": records,
        "excluded": sorted(
            scope_a["excluded_records"] + scope_b["excluded_records"],
            key=lambda item: item["element"]["element_key"],
        ),
        "skipped": skipped,
        "errors": errors,
        "semantics": SEMANTICS,
        "reproduction": reproduction_commands(),
    }
    result["result_digest"] = _digest(result)
    return result, timings


Pair = tuple[int, int]


def _compare(
    model_a: LoadedModel,
    model_b: LoadedModel,
    set_a: list[Any],
    set_b: list[Any],
    config: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    tolerance = float(config["tolerance_m"])
    exact, timings = _exact_relations(model_a, model_b, set_a, set_b, config)
    mesh, mesh_timings = _mesh_relations(model_a, model_b, set_a, set_b, config)
    timings.update(mesh_timings)

    records: list[dict[str, Any]] = []
    for pair in sorted(set(exact) | set(mesh)):
        entity_a, entity_b = model_a.file.by_id(pair[0]), model_b.file.by_id(pair[1])
        exact_relation = exact.get(pair)
        mesh_evidence = mesh.get(pair)
        mesh_relation = None if mesh_evidence is None else mesh_evidence["relation"]
        if exact_relation is None:
            # Never promote mesh-only evidence: record it as unsupported for review.
            classification, detail = "unsupported", "engine_disagreement"
        else:
            classification, detail = exact_relation
        overlap_box = _aabb_overlap([model_a.world_aabbs[pair[0]], model_b.world_aabbs[pair[1]]])
        records.append(
            {
                "a": _element_ref(model_a, entity_a),
                "b": _element_ref(model_b, entity_b),
                "classification": classification,
                "detail": detail,
                "tolerance_m": tolerance,
                "cross_check": {
                    "engine": config["cross_check_engine"],
                    "classification": "not_detected" if mesh_relation is None else mesh_relation,
                    "agrees": mesh_relation == (None if exact_relation is None else classification),
                    "engine_penetration_distance_m": None
                    if mesh_evidence is None
                    else mesh_evidence["distance"],
                    "engine_clash_type": None
                    if mesh_evidence is None
                    else ENGINE_CLASH_TYPES.get(mesh_evidence["clash_type"], "unknown"),
                },
                "representative_points_m": None
                if mesh_evidence is None
                else {
                    "a": mesh_evidence["p_a"],
                    "b": mesh_evidence["p_b"],
                    "note": "Mesh-engine contact/penetration points; not an overlap centroid.",
                },
                "aabb_overlap_m": None
                if overlap_box is None
                else {"min": list(overlap_box[0]), "max": list(overlap_box[1])},
                "status": "raw_geometric_result",
                "professional_action": "not_assessed",
            }
        )
    records.sort(key=lambda item: (item["a"]["element_key"], item["b"]["element_key"]))
    return records, timings


def _exact_relations(
    model_a: LoadedModel,
    model_b: LoadedModel,
    set_a: list[Any],
    set_b: list[Any],
    config: Mapping[str, Any],
) -> tuple[dict[Pair, tuple[str, str]], dict[str, float]]:
    """Classify with exact B-rep selection: shrink, exact and grown query shapes."""
    started = time.perf_counter()
    settings = ifcopenshell.geom.settings()
    settings.set("iterator-output", ifcopenshell.ifcopenshell_wrapper.NATIVE)
    tree = ifcopenshell.geom.tree(backend=config["primary_engine"])
    for model, elements in ((model_a, set_a), (model_b, set_b)):
        iterator = ifcopenshell.geom.iterator(
            settings, model.file, 1, include=elements, geometry_library=config["geometry_library"]
        )
        if not iterator.initialize():
            raise FeasibilityError(f"{model.member_id}: exact geometry could not be initialised.")
        tree.add_iterator(iterator)
    timings = {"exact_tree_build_seconds": time.perf_counter() - started}

    pointer_b = model_b.file.file_pointer()
    allowed_b = {element.id() for element in set_b}

    def selected(element: Any, extend: float) -> set[int]:
        found = tree.select(element, extend=extend)
        return {item.id() for item in found if item.file_pointer() == pointer_b} & allowed_b

    tolerance = float(config["tolerance_m"])
    started = time.perf_counter()
    relations: dict[Pair, tuple[str, str]] = {}
    for element in set_a:
        hard = selected(element, -tolerance)
        overlap = selected(element, 0.0)
        contact = selected(element, float(config["contact_epsilon_m"]))
        for b_id in sorted(hard | overlap | contact):
            pair = (element.id(), b_id)
            if b_id in hard:
                relations[pair] = ("hard_intersection", "penetration_exceeds_tolerance")
            elif b_id in overlap:
                relations[pair] = ("touch_contact", "overlap_not_exceeding_tolerance")
            else:
                relations[pair] = ("touch_contact", "surface_contact")
    timings["exact_query_seconds"] = time.perf_counter() - started
    return relations, timings


def _mesh_relations(
    model_a: LoadedModel,
    model_b: LoadedModel,
    set_a: list[Any],
    set_b: list[Any],
    config: Mapping[str, Any],
) -> tuple[dict[Pair, dict[str, Any]], dict[str, float]]:
    """Cross-check with the triangulated BVH engine, which also supplies contact points."""
    started = time.perf_counter()
    tree = ifcopenshell.geom.tree(backend=config["cross_check_engine"])
    for model, elements in ((model_a, set_a), (model_b, set_b)):
        for element in elements:
            tree.add_element(model.shapes[element.id()])
    timings = {"mesh_tree_build_seconds": time.perf_counter() - started}

    tolerance = float(config["tolerance_m"])
    started = time.perf_counter()
    hard = _collect(
        tree.clash_intersection_many(set_a, set_b, tolerance=tolerance, check_all=True),
        model_a,
        model_b,
    )
    touching = _collect(
        tree.clash_collision_many(set_a, set_b, allow_touching=True), model_a, model_b
    )
    timings["mesh_query_seconds"] = time.perf_counter() - started
    evidence: dict[Pair, dict[str, Any]] = {}
    for pair in set(hard) | set(touching):
        source = hard.get(pair) or touching[pair]
        relation = "hard_intersection" if pair in hard else "touch_contact"
        evidence[pair] = {**source, "relation": relation, "distance": _round(source["distance"])}
    return evidence, timings


def _collect(
    clashes: Sequence[Any], model_a: LoadedModel, model_b: LoadedModel
) -> dict[Pair, dict[str, Any]]:
    pointer_a, pointer_b = model_a.file.file_pointer(), model_b.file.file_pointer()
    collected: dict[Pair, dict[str, Any]] = {}
    for clash in clashes:
        entity_a, entity_b = clash.a, clash.b
        point_a, point_b = clash.p1, clash.p2
        # The engine does not preserve A/B order; resolve each side by its source file.
        if entity_a.file_pointer() == pointer_b and entity_b.file_pointer() == pointer_a:
            entity_a, entity_b = entity_b, entity_a
            point_a, point_b = point_b, point_a
        if entity_a.file_pointer() != pointer_a or entity_b.file_pointer() != pointer_b:
            raise FeasibilityError("Clash result could not be attributed to its source models.")
        # Entities returned by the engine do not outlive the result list; keep ids only.
        key = (int(entity_a.id()), int(entity_b.id()))
        candidate = {
            "distance": float(clash.distance),
            "clash_type": int(clash.clash_type),
            "p_a": [_round(value) for value in point_a],
            "p_b": [_round(value) for value in point_b],
        }
        existing = collected.get(key)
        if existing is None or candidate["distance"] > existing["distance"]:
            collected[key] = candidate
    return collected


def _scope(
    model: LoadedModel, include: Sequence[str], exclusions: Sequence[Mapping[str, str]]
) -> dict[str, Any]:
    in_scope: list[Any] = []
    excluded: list[Any] = []
    excluded_records: list[dict[str, Any]] = []
    out_of_scope = 0
    for product in sorted(model.file.by_type("IfcProduct"), key=lambda item: item.id()):
        reason = next(
            (rule["reason"] for rule in exclusions if product.is_a(rule["ifc_class"])), None
        )
        if reason is not None:
            excluded.append(product)
            excluded_records.append({"element": _element_ref(model, product), "reason": reason})
        elif any(product.is_a(ifc_class) for ifc_class in include):
            in_scope.append(product)
        elif product.is_a("IfcElement"):
            out_of_scope += 1
    return {
        "in_scope": in_scope,
        "excluded": excluded,
        "excluded_records": excluded_records,
        "out_of_scope": out_of_scope,
    }


def _skipped(model: LoadedModel, in_scope: Sequence[Any]) -> list[dict[str, Any]]:
    skipped = []
    for element in in_scope:
        reason = model.geometry_failures.get(element.id())
        if reason is None and element.id() not in model.shapes:
            reason = "geometry_not_produced"
        if reason is not None:
            skipped.append(
                {
                    "element": _element_ref(model, element),
                    "classification": "unsupported",
                    "reason": reason,
                }
            )
    return sorted(skipped, key=lambda item: item["element"]["element_key"])


# ---------------------------------------------------------------------------------------------
# Browser hand-off probe


def run_viewer_probe(models: Sequence[LoadedModel]) -> dict[str, Any]:
    """Load the models through installed web-ifc and the fragments autoCoordinate rule."""
    node = shutil.which("node")
    web_ifc = REPO_ROOT / "frontend" / "node_modules" / "web-ifc"
    if node is None:
        return {"status": "unavailable", "reason": "node executable not found"}
    if not web_ifc.is_dir():
        return {"status": "unavailable", "reason": "frontend/node_modules/web-ifc not installed"}
    arguments = [node, str(VIEWER_PROBE)] + [f"{m.member_id}={m.path}" for m in models]
    started = time.perf_counter()
    completed = subprocess.run(
        arguments, capture_output=True, text=True, timeout=300, check=False, cwd=REPO_ROOT
    )
    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        return {"status": "error", "reason": completed.stderr.strip()[-2000:]}
    probe = json.loads(completed.stdout)

    offsets: list[np.ndarray] = []
    compared = 0
    missing: list[str] = []
    per_model = []
    for model, probed in zip(models, probe["models"], strict=True):
        by_id = {element["express_id"]: element for element in probed["elements"]}
        for express_id, (low, high) in sorted(model.world_aabbs.items()):
            element = by_id.get(express_id)
            if element is None:
                missing.append(f"{model.member_id}#{express_id}")
                continue
            # web-ifc emits Y-up geometry: IFC (x, y, z) maps to viewer (x, z, -y).
            yup_low = np.array([low[0], low[2], -high[1]])
            yup_high = np.array([high[0], high[2], -low[1]])
            offsets.append(np.asarray(element["min"]) - yup_low)
            offsets.append(np.asarray(element["max"]) - yup_high)
            compared += 1
        per_model.append(
            {
                "member_id": model.member_id,
                "coordination_translation": [
                    _round(v) for v in probed["coordination_matrix"][12:15]
                ],
                "fragments_translation": [_round(v) for v in probed["fragments_translation"]],
                "streamed_elements": len(probed["elements"]),
            }
        )
    if not offsets:
        return {"status": "error", "reason": "No comparable elements.", "missing": missing}
    stacked = np.vstack(offsets)
    spread = float(np.max(stacked.max(axis=0) - stacked.min(axis=0)))
    consistent = spread <= VIEWER_TOLERANCE_M and not missing
    return {
        "status": "consistent" if consistent else "inconsistent",
        "web_ifc_version": probe["web_ifc_version"],
        "import_settings": probe["import_settings"],
        "coordination_rule": probe["coordination_rule"],
        "frame_mapping": "viewer = (x, z, -y) + common_offset",
        "common_offset_m": [_round(v) for v in stacked.mean(axis=0)],
        "max_offset_spread_m": spread,
        "tolerance_m": VIEWER_TOLERANCE_M,
        "compared_elements": compared,
        "missing_elements": missing,
        "models": per_model,
        "probe_seconds": elapsed,
    }


# ---------------------------------------------------------------------------------------------
# Feasibility run and report


def reproduction_commands() -> list[str]:
    return [
        "python -c \"import sys; sys.path.insert(0, 'tests'); "
        'from feasibility.coordination import main; raise SystemExit(main())"',
        "python -m pytest tests/feasibility -q",
        "node tests/feasibility/webifc_viewer_probe.mjs "
        f"ARC=datasets/synthetic/generated/fed001/{ARC_FILE} "
        f"MEP=datasets/synthetic/generated/fed001/{MEP_FILE}",
    ]


def load_model_set(manifest_path: Path) -> tuple[dict[str, Any], list[LoadedModel]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    models = [
        load_model(member["member_id"], member["discipline"], manifest_path.parent / member["file"])
        for member in manifest["members"]
    ]
    return manifest, models


def evaluate_go(
    first: dict[str, Any],
    second: dict[str, Any],
    models: Sequence[LoadedModel],
    viewer: Mapping[str, Any],
) -> dict[str, Any]:
    expectations = analytic_expectations(first["configuration"])
    observed = {(item["a"]["name"], item["b"]["name"]): item for item in first["intersections"]}
    mismatches = []
    for pair, expected in sorted(expectations.items()):
        actual = observed.get(pair)
        relation = "separated" if actual is None else actual["classification"]
        if relation != expected["relation"]:
            mismatches.append({"pair": list(pair), "expected": expected, "observed": relation})
    unexpected = sorted(set(observed) - set(expectations))
    hard_expected = [p for p, e in expectations.items() if e["relation"] == "hard_intersection"]
    separated = [p for p, e in expectations.items() if e["relation"] == "separated"]
    identity_ok = bool(first["intersections"]) and all(
        side["member_id"] and side["model_sha256"] and side["element_key"]
        for item in first["intersections"]
        for side in (item["a"], item["b"])
    )
    criteria = {
        "1_independently_parseable": all(
            model.profile["geometry"]["status"] in {"loaded", "partial"} for model in models
        ),
        "2_consistent_coordinate_frame": first["alignment"]["status"] == "aligned",
        "3_real_intersection_detected": bool(hard_expected)
        and all(
            observed.get(p, {}).get("classification") == "hard_intersection" for p in hard_expected
        ),
        "4_known_non_intersection_absent": bool(separated)
        and all(p not in observed for p in separated),
        "5_reproduced_on_rerun": first["result_digest"] == second["result_digest"],
        "6_source_model_and_element_identified": identity_ok,
        "7_browser_rendering_path_compatible": viewer.get("status") == "consistent",
    }
    return {
        "decision": "GO"
        if all(criteria.values()) and not mismatches and not unexpected
        else "NO-GO",
        "criteria": criteria,
        "oracle_mismatches": mismatches,
        "unexpected_pairs": [list(pair) for pair in unexpected],
        "oracle": {f"{a}|{b}": value for (a, b), value in sorted(expectations.items())},
    }


def proposed_handoff() -> dict[str, Any]:
    return {
        "status": "proposal_only_not_implemented",
        "model_set_manifest": {
            "schema": MANIFEST_SCHEMA,
            "fields": [
                "model_set_id",
                "common_frame{projected_crs, map_conversion, length_unit, transform}",
                "members[{member_id, discipline, session_id, sha256, schema}]",
            ],
        },
        "api": [
            "POST /model-sets -> 201 ModelSet | 422 alignment rejected (reasons[])",
            "GET /model-sets/{model_set_id}",
            "POST /model-sets/{model_set_id}/coordination-runs "
            "{pair, include_a, include_b, exclusions, tolerance_m} -> 202 run_id",
            "GET /model-sets/{model_set_id}/coordination-runs/{run_id} -> clash result",
            "GET /sessions/{session_id}/model/file (existing; ETag = sha256) per member",
        ],
        "browser": [
            "One FragmentsManager; IfcLoader.load(bytes, true, member_id) per member in "
            "manifest order so the first member defines base coordinates.",
            "Highlight with a ModelIdMap keyed by member_id; resolve GlobalIds per model with "
            "getLocalIdsByGuids, never across models.",
            "fragments autoCoordinate applies translation only; rotated or mismatched "
            "georeferencing must be rejected by the federation gate before rendering.",
            "The existing single-model Session and production React viewer are unchanged.",
        ],
    }


def run_feasibility(
    fixture_dir: Path = DEFAULT_FIXTURE_DIR,
    report_dir: Path = DEFAULT_REPORT_DIR,
    *,
    viewer_probe: bool = True,
) -> dict[str, Any]:
    _, _, manifest_path = generate_fixtures(fixture_dir)
    manifest, models = load_model_set(manifest_path)
    first, timings = run_clash(models, manifest)
    # Rerun from freshly parsed files to prove reproducibility, not object reuse.
    rerun_manifest, rerun_models = load_model_set(manifest_path)
    second, _ = run_clash(rerun_models, rerun_manifest)
    viewer = (
        run_viewer_probe(models) if viewer_probe else {"status": "unavailable", "reason": "skipped"}
    )
    result_bytes = _json_bytes(first)
    report = {
        "schema": REPORT_SCHEMA,
        "task": "FED-001",
        "data_class": "synthetic",
        "private_models_accessed": False,
        "statement": (
            "Synthetic feasibility evidence only. Not a measurement of real-world clash "
            "detection performance or accuracy."
        ),
        "models": [model.profile for model in models],
        "alignment": first["alignment"],
        "result_digest": first["result_digest"],
        "rerun_result_digest": second["result_digest"],
        "summary": first["summary"],
        "go_no_go": evaluate_go(first, second, models, viewer),
        "viewer_probe": viewer,
        "engine_findings": [
            "opencascade.brep supports only select/select_box (exact B-rep, NATIVE iterator "
            "output); clash_*_many queries require opencascade.trianglebvh.",
            "opencascade.trianglebvh intersection and collision queries missed coplanar-face "
            "overlaps (an exact duplicate box and a partially offset coincident box) during "
            "exploration, although the flush-embedded fixture pair is detected. Exact B-rep "
            "selection is therefore the primary classifier and the mesh engine is a recorded "
            "cross-check.",
            "cgal and hybrid geometry libraries reported a spurious 0.0833 m penetration for a "
            "1 mm overlap during exploration; geometry_library is pinned to opencascade.",
            "Mesh clash results do not preserve A/B order and their entity wrappers do not "
            "outlive the result list; sides are resolved by source file and ids copied at once.",
            "The mesh engine's penetration distance is engine-defined (0.2236 m reported for a "
            "0.2 m through-penetration); it is reported as engine evidence, not a depth.",
            "clash_clearance_many did not report a touching pair; it is not used.",
        ],
        "performance": {
            "parse_seconds": {m.member_id: m.timings["parse_seconds"] for m in models},
            "geometry_seconds": {m.member_id: m.timings["geometry_seconds"] for m in models},
            **timings,
            "result_bytes": len(result_bytes),
            "ifc_bytes": {m.member_id: m.profile["size_bytes"] for m in models},
            "note": "Single local run on tiny synthetic models; not a scalability measurement.",
        },
        "proposed_handoff": proposed_handoff(),
        "reproduction": reproduction_commands(),
    }
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "fed001-clash-result.json").write_bytes(result_bytes)
    (report_dir / "coordination-feasibility.json").write_bytes(_json_bytes(report))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FED-001 two-model clash feasibility")
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--no-viewer-probe", action="store_true")
    args = parser.parse_args(argv)
    report = run_feasibility(
        args.fixture_dir, args.report_dir, viewer_probe=not args.no_viewer_probe
    )
    decision = report["go_no_go"]
    print(
        json.dumps({"decision": decision["decision"], "criteria": decision["criteria"]}, indent=2)
    )
    print(f"result_digest={report['result_digest']} rerun={report['rerun_result_digest']}")
    print(f"report={args.report_dir / 'coordination-feasibility.json'}")
    return 0 if decision["decision"] == "GO" else 1


# ---------------------------------------------------------------------------------------------
# Helpers


def _create(model: Any, ifc_class: str, name: str) -> Any:
    return ifcopenshell.api.root.create_entity(model, ifc_class=ifc_class, name=name)


def _set_placement(model: Any, product: Any, origin: Vec3) -> None:
    matrix = np.eye(4)
    matrix[:3, 3] = origin
    ifcopenshell.api.geometry.edit_object_placement(model, product=product, matrix=matrix)


def _add_map_conversion(model: Any, context: Any, georeference: GeoReference) -> None:
    crs = model.create_entity("IfcProjectedCRS", Name=georeference.crs_name)
    model.create_entity(
        "IfcMapConversion",
        SourceCRS=context,
        TargetCRS=crs,
        Eastings=georeference.eastings,
        Northings=georeference.northings,
        OrthogonalHeight=georeference.orthogonal_height,
        XAxisAbscissa=georeference.x_axis_abscissa,
        XAxisOrdinate=georeference.x_axis_ordinate,
        Scale=georeference.scale,
    )


def _georeference_record(georeference: GeoReference) -> dict[str, Any]:
    return {
        "target_crs": georeference.crs_name,
        "eastings": georeference.eastings,
        "northings": georeference.northings,
        "orthogonal_height": georeference.orthogonal_height,
        "x_axis_abscissa": georeference.x_axis_abscissa,
        "x_axis_ordinate": georeference.x_axis_ordinate,
        "scale": georeference.scale,
    }


def _map_conversions(ifc: Any) -> list[Any]:
    try:
        return sorted(ifc.by_type("IfcMapConversion"), key=lambda item: item.id())
    except RuntimeError:  # schema without IfcMapConversion, e.g. IFC2X3
        return []


def _map_conversion_record(conversion: Any) -> dict[str, Any]:
    def number(value: Any, default: float) -> float:
        return float(default if value is None else value)

    return {
        "target_crs": getattr(conversion.TargetCRS, "Name", None),
        "eastings": float(conversion.Eastings),
        "northings": float(conversion.Northings),
        "orthogonal_height": float(conversion.OrthogonalHeight),
        "x_axis_abscissa": number(conversion.XAxisAbscissa, 1.0),
        "x_axis_ordinate": number(conversion.XAxisOrdinate, 0.0),
        "scale": number(conversion.Scale, 1.0),
    }


def _model_contexts(ifc: Any) -> list[Any]:
    return [
        context
        for context in ifc.by_type("IfcGeometricRepresentationContext")
        if not context.is_a("IfcGeometricRepresentationSubContext")
        and context.ContextType == "Model"
    ]


def _context_record(context: Any) -> dict[str, Any]:
    placement = context.WorldCoordinateSystem

    def ratios(direction: Any) -> list[float] | None:
        return None if direction is None else [float(v) for v in direction.DirectionRatios]

    return {
        "dimension": context.CoordinateSpaceDimension,
        "world_origin": [float(v) for v in placement.Location.Coordinates],
        "world_axis": ratios(getattr(placement, "Axis", None)),
        "world_ref_direction": ratios(getattr(placement, "RefDirection", None)),
        "true_north": ratios(context.TrueNorth),
    }


def _same_record(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if set(left) != set(right):
        return False
    for key, value in left.items():
        other = right[key]
        if isinstance(value, float) and isinstance(other, (int, float)):
            if abs(value - float(other)) > FRAME_TOLERANCE:
                return False
        elif value != other:
            return False
    return True


def _element_ref(model: LoadedModel, entity: Any) -> dict[str, Any]:
    global_id = getattr(entity, "GlobalId", None)
    identity = global_id if global_id else f"#{entity.id()}:{entity.is_a()}"
    return {
        "member_id": model.member_id,
        "model_sha256": model.sha256,
        "global_id": global_id,
        "express_id": entity.id(),
        "ifc_type": entity.is_a(),
        "name": getattr(entity, "Name", None),
        "element_key": f"{model.member_id}|{model.sha256}|{identity}",
    }


def _model_identity(model: LoadedModel) -> dict[str, Any]:
    return {
        "member_id": model.member_id,
        "discipline": model.discipline,
        "file": model.path.name,
        "sha256": model.sha256,
        "schema": model.file.schema_identifier,
    }


def _reason(code: str, member_id: str, detail: str) -> dict[str, str]:
    return {"code": code, "member_id": member_id, "detail": detail}


def _in_scope_specs(
    discipline: str, include: Sequence[str], exclusions: Sequence[Mapping[str, str]]
) -> list[ElementSpec]:
    schema = ifcopenshell.ifcopenshell_wrapper.schema_by_name("IFC4")

    def is_a(ifc_class: str, parent: str) -> bool:
        declaration: Any = schema.declaration_by_name(ifc_class)
        while declaration is not None:
            if declaration.name().lower() == parent.lower():
                return True
            declaration = declaration.supertype()
        return False

    return [
        spec
        for spec in ELEMENT_SPECS[discipline]
        if spec.has_body
        and any(is_a(spec.ifc_class, name) for name in include)
        and not any(is_a(spec.ifc_class, rule["ifc_class"]) for rule in exclusions)
    ]


def _vec(values: Any) -> Vec3:
    return (_round(values[0]), _round(values[1]), _round(values[2]))


def _round(value: float) -> float:
    rounded = round(float(value), COORDINATE_DECIMALS)
    return 0.0 if rounded == 0 else rounded


def _round_nested(rows: list[list[float]]) -> list[list[float]]:
    return [[_round(value) for value in row] for row in rows]


def _union_aabb(boxes: Any) -> Aabb | None:
    items = list(boxes)
    if not items:
        return None
    low = tuple(min(box[0][i] for box in items) for i in range(3))
    high = tuple(max(box[1][i] for box in items) for i in range(3))
    return (low[0], low[1], low[2]), (high[0], high[1], high[2])


def _aabb_overlap(boxes: Sequence[Aabb]) -> Aabb | None:
    low = tuple(max(box[0][i] for box in boxes) for i in range(3))
    high = tuple(min(box[1][i] for box in boxes) for i in range(3))
    if any(low[i] > high[i] for i in range(3)):
        return None
    return (_round(low[0]), _round(low[1]), _round(low[2])), (
        _round(high[0]),
        _round(high[1]),
        _round(high[2]),
    )


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
