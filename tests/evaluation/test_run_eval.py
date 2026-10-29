from __future__ import annotations

import json
from pathlib import Path

from bim_intelligence.schemas import CheckResult
from evaluation.benchmark import generate_benchmark
from evaluation.run_eval import _ifctester_json_default, _status_summary, evaluate


def test_complete_offline_evaluation_reports_measured_results(tmp_path: Path) -> None:
    artifacts = generate_benchmark(tmp_path / "benchmark")
    result, ifctester_report = evaluate(artifacts)

    assert result["composition"]["positive_defect_count"] == 15
    assert result["composition"]["clean_control_count"] == 7
    assert result["dataset_version"] == "1.0.0"
    assert len(result["versions"]["checks"]) == 11
    assert (
        result["versions"]["checks"]["classification.consistent_by_type"]["rule_version"] == "1.0.0"
    )
    assert result["metrics"]["aggregate"] == {
        "tp": 15,
        "fp": 0,
        "fn": 0,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
    }
    assert result["metrics"]["by_rule_family"] == {
        family: {
            "tp": count,
            "fp": 0,
            "fn": 0,
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
        }
        for family, count in {
            "property.required": 7,
            "naming.pattern": 4,
            "classification.*": 4,
        }.items()
    }
    assert result["clean_controls"]["false_positives_on_clean_model"] == 0
    assert result["clean_controls"]["false_positives_on_defective_model_controls"] == 0
    assert result["determinism"]["byte_identical_findings_json"] is True
    assert result["ifctester_baseline"]["agreement"] is True
    assert result["ifctester_baseline"]["normalised_ids_entity_failures"] == 14
    assert result["ifctester_baseline"]["ifctester_json_entity_failures"] == 14
    assert result["execution"]["defective"]["errored"] == []
    assert result["execution"]["defective"]["skipped"] == []
    assert len(result["execution"]["defective"]["not_applicable"]) == 1
    assert result["model"]["invoked"] is False
    assert result["model"]["llm_mode"] == "off"
    assert result["model"]["network_calls"] == 0
    assert result["model"]["live_api_requests"] == 0
    assert result["model"]["live_spend_usd"] == "0"
    assert result["offline_ai_safety_evaluation"]["passed"] == 9
    assert result["offline_ai_safety_evaluation"]["network_calls"] == 0
    assert ifctester_report["title"] == "BIM Intelligence synthetic architectural benchmark"
    serialised_report = json.loads(
        json.dumps(ifctester_report, default=_ifctester_json_default, sort_keys=True)
    )
    assert serialised_report["title"] == ifctester_report["title"]


def test_unexecuted_and_non_applicable_checks_remain_separate_from_findings() -> None:
    summary = _status_summary(
        [
            CheckResult(
                check_id="skipped-check",
                requirement_id="REQ-SKIPPED",
                status="skipped",
                applicable_count=0,
            ),
            CheckResult(
                check_id="error-check",
                requirement_id="REQ-ERROR",
                status="error",
                applicable_count=0,
                diagnostics=["Synthetic execution error."],
            ),
            CheckResult(
                check_id="not-applicable-check",
                requirement_id="REQ-NA",
                status="not_applicable",
                applicable_count=0,
            ),
            CheckResult(
                check_id="passed-check",
                requirement_id="REQ-PASSED",
                status="passed",
                applicable_count=1,
            ),
        ]
    )

    assert summary["check_count"] == 4
    assert summary["status_counts"] == {
        "error": 1,
        "not_applicable": 1,
        "passed": 1,
        "skipped": 1,
    }
    assert [item["check_id"] for item in summary["skipped"]] == ["skipped-check"]
    assert [item["check_id"] for item in summary["errored"]] == ["error-check"]
    assert [item["check_id"] for item in summary["not_applicable"]] == ["not-applicable-check"]
