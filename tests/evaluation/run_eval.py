"""Run the offline deterministic benchmark and write JSON/Markdown evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import socket
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import ifcopenshell
import ifctester.ids
import ifctester.reporter

from bim_intelligence.bim import ingest_model
from bim_intelligence.config import LLMMode, Settings
from bim_intelligence.orchestration.runner import run_review
from bim_intelligence.requirements import confirm_classification_consistency, import_ids_document
from bim_intelligence.schemas import Finding, findings_to_json
from bim_intelligence.store import FINDINGS_FILE, RUNS_DIR, SessionStore
from evaluation.benchmark import (
    DEFAULT_OUTPUT_DIR,
    BenchmarkArtifacts,
    control_false_positives,
    finding_record,
    generate_benchmark,
    metrics,
    validate_ground_truth,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_DIR = REPOSITORY_ROOT / "tests" / "evaluation" / "runs" / "latest"
MAX_IFC_BYTES = 200 * 1024 * 1024
MAX_IDS_BYTES = 25 * 1024 * 1024


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    artifacts = generate_benchmark(args.benchmark_dir)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    result, ifctester_report = evaluate(artifacts)
    (args.results_dir / "ifctester-results.json").write_text(
        json.dumps(
            ifctester_report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_ifctester_json_default,
        )
        + "\n",
        encoding="utf-8",
    )
    (args.results_dir / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = _summary_markdown(result)
    (args.results_dir / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    print(f"Machine-readable results: {args.results_dir / 'results.json'}")
    print(f"IfcTester JSON report: {args.results_dir / 'ifctester-results.json'}")
    return 0


def evaluate(artifacts: BenchmarkArtifacts) -> tuple[dict[str, Any], dict[str, Any]]:
    tests_path = str(REPOSITORY_ROOT / "tests")
    if tests_path not in sys.path:
        sys.path.insert(0, tests_path)
    attempts: list[str] = []

    def blocked_connect(_socket: socket.socket, address: Any) -> None:
        attempts.append(repr(address))
        raise AssertionError(f"Network access is forbidden in offline evaluation: {address!r}")

    def blocked_connect_ex(_socket: socket.socket, address: Any) -> int:
        attempts.append(repr(address))
        raise AssertionError(f"Network access is forbidden in offline evaluation: {address!r}")

    with (
        patch.object(socket.socket, "connect", blocked_connect),
        patch.object(socket.socket, "connect_ex", blocked_connect_ex),
    ):
        result, report = _evaluate(artifacts)
    result["model"]["network_calls"] = len(attempts)
    return result, report


def _evaluate(artifacts: BenchmarkArtifacts) -> tuple[dict[str, Any], dict[str, Any]]:
    ground_truth = json.loads(artifacts.ground_truth.read_text(encoding="utf-8"))
    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    validate_ground_truth(artifacts)
    expected = ground_truth["positive_defects"]
    family_by_rule = {item["rule_id"]: item["rule_family"] for item in manifest["checks"]}

    with tempfile.TemporaryDirectory(prefix="bimi-t6-") as runtime_dir:
        settings = Settings(
            _env_file=None,
            data_dir=Path(runtime_dir),
            llm_mode=LLMMode.OFF,
            max_plan_checks=50,
            max_tool_calls_per_run=100,
        )
        if settings.llm_mode is not LLMMode.OFF:
            raise RuntimeError("The deterministic benchmark requires LLM_MODE=off.")
        store = SessionStore(settings.data_dir / "sessions")
        clean_findings, clean_statuses, _ = _review(
            store, settings, artifacts.clean_ifc.read_bytes(), artifacts.ids.read_bytes()
        )
        defective_findings_1, defective_statuses, defective_bytes_1 = _review(
            store, settings, artifacts.defective_ifc.read_bytes(), artifacts.ids.read_bytes()
        )
        _defective_findings_2, repeated_statuses, defective_bytes_2 = _review(
            store, settings, artifacts.defective_ifc.read_bytes(), artifacts.ids.read_bytes()
        )

    predictions = [finding_record(finding) for finding in defective_findings_1]
    metrics_by_rule = _metrics_by_family(expected, predictions, family_by_rule)
    aggregate = metrics(expected, predictions)
    clean_control_false_positives = control_false_positives(
        predictions, ground_truth["clean_controls"]
    )
    clean_model_false_positives = [finding_record(finding) for finding in clean_findings]
    execution = {
        "defective": _status_summary(defective_statuses),
        "clean": _status_summary(clean_statuses),
        "repeated_defective": _status_summary(repeated_statuses),
    }

    ifctester_summary, ifctester_report = _ifctester_baseline(artifacts, defective_findings_1)
    from evaluation.offline_ai import evaluate_offline_ai

    offline_ai = evaluate_offline_ai()
    data_hashes = _sha256s(artifacts)
    result = {
        "report_version": "1.0.0",
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "working_tree_dirty": _working_tree_dirty(),
        "dataset_id": ground_truth["dataset_id"],
        "dataset_version": ground_truth["ground_truth_version"],
        "dataset_hashes": data_hashes,
        "model": {
            "configured_model": "muse-spark-1.3",
            "invoked": False,
            "llm_mode": settings.llm_mode.value,
            "live_api_requests": 0,
            "live_spend_usd": "0",
        },
        "versions": {
            "python": platform.python_version(),
            "ifcopenshell": getattr(ifcopenshell, "version", "unknown"),
            "ifctester": _ifctester_version(),
            "ids_document_sha256": _sha256(artifacts.ids.read_bytes()),
            "checks": {
                item["check_name"]: {
                    "rule_id": item["rule_id"],
                    "check_id": item["check_id"],
                    "rule_version": item["rule_version"],
                    "implemented": item["implemented"],
                }
                for item in manifest["checks"]
            },
        },
        "composition": _composition(artifacts, expected, ground_truth, manifest),
        "ground_truth": {
            "positive_p0_defects": len(expected),
            "clean_controls": len(ground_truth["clean_controls"]),
            "p1_defects_tested": 0,
            "supported_p0_categories": manifest["supported_p0_categories"],
            "unsupported_p0_categories": manifest["unsupported_p0_categories"],
            "unsupported_p1_categories": manifest["unsupported_p1_categories"],
        },
        "metrics": {
            "aggregate": aggregate,
            "by_rule_family": metrics_by_rule,
            "target": {"precision": 0.90, "recall": 0.90},
            "target_met": bool(
                aggregate["precision"] is not None
                and aggregate["recall"] is not None
                and aggregate["precision"] >= 0.90
                and aggregate["recall"] >= 0.90
            ),
            "predictions": predictions,
            "duplicate_prediction_count": _duplicate_count(predictions),
            "unmatched_predictions": _unmatched(expected, predictions),
            "missed_defects": _missed(expected, predictions),
        },
        "clean_controls": {
            "false_positives_on_clean_model": len(clean_model_false_positives),
            "clean_model_predictions": clean_model_false_positives,
            "false_positives_on_defective_model_controls": len(clean_control_false_positives),
            "defective_model_control_predictions": clean_control_false_positives,
        },
        "determinism": {
            "byte_identical_findings_json": defective_bytes_1 == defective_bytes_2,
            "first_sha256": _sha256(defective_bytes_1),
            "second_sha256": _sha256(defective_bytes_2),
            "finding_count": len(defective_findings_1),
        },
        "ifctester_baseline": ifctester_summary,
        "execution": execution,
        "offline_ai_safety_evaluation": offline_ai,
        "limitations": [
            "The synthetic benchmark measures only its labelled IFC4 defect instances.",
            (
                "No live Muse Spark relevance, structured-output reliability, or token economics "
                "were measured."
            ),
            (
                "IDS tests cover property presence/value patterns, naming, and classification "
                "presence/system; relationship checks and duplicate-GlobalId checks remain "
                "unimplemented P1 gaps."
            ),
            "The planned D15-D17 P1 catalogue entries are not included in P0 metrics.",
            (
                "The benchmark's classification type/occurrence test covers the one registered "
                "native rule only."
            ),
        ],
    }
    return result, ifctester_report


def _review(
    store: SessionStore, settings: Settings, model_bytes: bytes, ids_bytes: bytes
) -> tuple[list[Finding], list[Any], bytes]:
    session = store.create()
    ingest_model(store, session.id, [model_bytes], max_bytes=MAX_IFC_BYTES)
    import_ids_document(store, session.id, ids_bytes, max_bytes=MAX_IDS_BYTES)
    confirm_classification_consistency(store, session.id)
    outcome = run_review(store, session.id, settings=settings)
    findings_path = store.session_dir(session.id) / RUNS_DIR / outcome.run.id / FINDINGS_FILE
    canonical = findings_path.read_bytes()
    if canonical != findings_to_json(outcome.findings).encode("utf-8"):
        raise RuntimeError("Persisted findings differ from canonical findings serialisation.")
    return outcome.findings, outcome.run.check_results, canonical


def _ifctester_baseline(
    artifacts: BenchmarkArtifacts, findings: list[Finding]
) -> tuple[dict[str, Any], dict[str, Any]]:
    model = ifcopenshell.open(str(artifacts.defective_ifc))
    ids = ifctester.ids.open(str(artifacts.ids), validate=True)
    ids.validate(model)
    reporter = ifctester.reporter.Json(ids)
    report = reporter.report()

    reported: Counter[tuple[str, int, str, str]] = Counter()
    for spec in report["specifications"]:
        for facet_index, requirement in enumerate(spec["requirements"]):
            for entity in requirement["failed_entities"]:
                global_id = entity.get("global_id")
                reason = entity.get("reason")
                if not isinstance(global_id, str) or not isinstance(reason, str):
                    raise ValueError("IfcTester failure entity is missing its GlobalId or reason")
                reported[
                    (
                        f"ids:{spec['name']}",
                        facet_index,
                        global_id,
                        reason,
                    )
                ] += 1
    normalised: Counter[tuple[str, int, str, str]] = Counter()
    for finding in findings:
        if finding.method != "ids":
            continue
        for element in finding.elements:
            if element.global_id is None:
                raise ValueError(f"IDS finding {finding.id} has an element without a GlobalId")
            normalised[
                (finding.rule_id, finding.facet_index, element.global_id, finding.observed)
            ] += 1
    matching = normalised == reported
    return (
        {
            "agreement": matching,
            "normalised_ids_entity_failures": sum(normalised.values()),
            "ifctester_json_entity_failures": sum(reported.values()),
            "missing_from_normaliser": _counter_rows(reported - normalised),
            "extra_in_normaliser": _counter_rows(normalised - reported),
        },
        report,
    )


def _ifctester_json_default(value: Any) -> str:
    if isinstance(value, ifcopenshell.entity_instance):
        return str(value)
    raise TypeError(f"IfcTester report contains unsupported JSON value: {type(value).__name__}")


def _metrics_by_family(
    expected: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    family_by_rule: dict[str, str],
) -> dict[str, dict[str, int | float | None]]:
    families = sorted(
        {item["rule_family"] for item in expected}
        | {family_by_rule.get(item["rule_id"], "unmatched") for item in predictions}
    )
    return {
        family: metrics(
            [item for item in expected if item["rule_family"] == family],
            [
                item
                for item in predictions
                if family_by_rule.get(item["rule_id"], "unmatched") == family
            ],
        )
        for family in families
    }


def _status_summary(results: list[Any]) -> dict[str, Any]:
    counts = Counter(result.status for result in results)
    return {
        "check_count": len(results),
        "status_counts": dict(sorted(counts.items())),
        "skipped": _result_rows(results, "skipped"),
        "errored": _result_rows(results, "error"),
        "not_applicable": _result_rows(results, "not_applicable"),
    }


def _result_rows(results: list[Any], status: str) -> list[dict[str, Any]]:
    return [
        {
            "check_id": item.check_id,
            "requirement_id": item.requirement_id,
            "diagnostics": item.diagnostics,
        }
        for item in results
        if item.status == status
    ]


def _unmatched(
    expected: list[dict[str, Any]], predicted: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    expected_keys = {_finding_key(item) for item in expected}
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    unmatched: list[dict[str, Any]] = []
    for prediction in predicted:
        key = _finding_key(prediction)
        if key not in expected_keys or key in seen:
            unmatched.append(prediction)
        seen.add(key)
    return unmatched


def _missed(
    expected: list[dict[str, Any]], predicted: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    prediction_keys = {_finding_key(item) for item in predicted}
    return [item for item in expected if _finding_key(item) not in prediction_keys]


def _finding_key(record: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    global_ids = record.get("global_ids")
    if global_ids is None:
        global_ids = [element["global_id"] for element in record.get("elements", [])]
    return (
        record["rule_id"],
        record.get("check_id", ""),
        tuple(sorted(global_ids)),
    )


def _duplicate_count(predictions: list[dict[str, Any]]) -> int:
    keys = [_finding_key(item) for item in predictions]
    return len(keys) - len(set(keys))


def _counter_rows(values: Counter[tuple[str, int, str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "rule_id": key[0],
            "facet_index": key[1],
            "global_id": key[2],
            "observed": key[3],
            "count": count,
        }
        for key, count in sorted(values.items())
    ]


def _composition(
    artifacts: BenchmarkArtifacts,
    defects: list[dict[str, Any]],
    ground_truth: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    model = ifcopenshell.open(str(artifacts.clean_ifc))
    counts = {
        ifc_type: len(model.by_type(ifc_type))
        for ifc_type in (
            "IfcProject",
            "IfcSite",
            "IfcBuilding",
            "IfcBuildingStorey",
            "IfcWall",
            "IfcDoor",
            "IfcWindow",
            "IfcSlab",
            "IfcSpace",
            "IfcWallType",
            "IfcClassificationReference",
            "IfcRelAssociatesClassification",
            "IfcRelDefinesByType",
            "IfcRelContainedInSpatialStructure",
            "IfcShapeRepresentation",
        )
    }
    families = Counter(item["rule_family"] for item in defects)
    return {
        "ifc_schema": model.schema_identifier,
        "element_counts": counts,
        "storey_names": sorted(item.Name for item in model.by_type("IfcBuildingStorey")),
        "positive_defects_by_rule_family": dict(sorted(families.items())),
        "positive_defect_count": len(defects),
        "clean_control_count": len(ground_truth["clean_controls"]),
        "implemented_check_count": sum(1 for item in manifest["checks"] if item["implemented"]),
        "implemented_checks_by_rule_family": dict(
            sorted(Counter(item["rule_family"] for item in manifest["checks"]).items())
        ),
        "non_applicable_control_count": len(ground_truth["non_applicable_controls"]),
    }


def _sha256s(artifacts: BenchmarkArtifacts) -> dict[str, str]:
    return {path.name: _sha256(path.read_bytes()) for path in artifacts.__dict__.values()}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _working_tree_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def _ifctester_version() -> str:
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("ifctester")
    except PackageNotFoundError as exc:
        raise RuntimeError("Could not determine the installed IfcTester version.") from exc


def _summary_markdown(result: dict[str, Any]) -> str:
    aggregate = result["metrics"]["aggregate"]
    composition = result["composition"]
    determinism = result["determinism"]
    baseline = result["ifctester_baseline"]
    return "\n".join(
        [
            "# T-6 offline benchmark result",
            "",
            f"- Dataset: `{result['dataset_id']}` ({composition['ifc_schema']})",
            f"- Positive P0 defects: {composition['positive_defect_count']}",
            f"- Clean controls: {composition['clean_control_count']}",
            f"- Predictions: TP {aggregate['tp']}, FP {aggregate['fp']}, FN {aggregate['fn']}",
            f"- Precision: {_format_metric(aggregate['precision'])}",
            f"- Recall: {_format_metric(aggregate['recall'])}",
            f"- F1: {_format_metric(aggregate['f1'])}",
            f"- >=90% precision and recall target met: {result['metrics']['target_met']}",
            (
                "- Byte-identical repeated findings JSON: "
                f"{determinism['byte_identical_findings_json']}"
            ),
            f"- IfcTester JSON entity-level agreement: {baseline['agreement']}",
            (
                "- Clean-model false positives: "
                f"{result['clean_controls']['false_positives_on_clean_model']}"
            ),
            (
                "- Defective-model control false positives: "
                f"{result['clean_controls']['false_positives_on_defective_model_controls']}"
            ),
            (
                "- Live Meta API calls / spend: "
                f"{result['model']['live_api_requests']} / USD {result['model']['live_spend_usd']}"
            ),
            "",
            "## Per-rule-family results",
            "",
            "| Rule family | TP | FP | FN | Precision | Recall | F1 |",
            "|---|---:|---:|---:|---:|---:|---:|",
            *[
                "| {family} | {tp} | {fp} | {fn} | {precision} | {recall} | {f1} |".format(
                    family=family,
                    tp=values["tp"],
                    fp=values["fp"],
                    fn=values["fn"],
                    precision=_format_metric(values["precision"]),
                    recall=_format_metric(values["recall"]),
                    f1=_format_metric(values["f1"]),
                )
                for family, values in result["metrics"]["by_rule_family"].items()
            ],
            "",
            (
                "This is deterministic validator evidence, not a measure of Muse Spark planning "
                "or explanation quality."
            ),
            "See `results.json` for execution errors, skips, hashes, and coverage gaps.",
            "",
        ]
    )


def _format_metric(value: float | None) -> str:
    return "undefined (zero denominator)" if value is None else f"{value:.3f}"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
