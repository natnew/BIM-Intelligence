"""CheckResult and ReviewRun: execution status is separate from defect findings (C-05)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from bim_intelligence.schemas import (
    CheckResult,
    InputManifest,
    PlannedCheck,
    ReviewPlan,
    ReviewRun,
)

T0 = datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 10, 27, 10, 0, 5, tzinfo=timezone.utc)
MANIFEST = InputManifest(
    model_hash="a" * 64,
    ids_hashes=["b" * 64],
    requirement_revisions={"REQ-001": 1, "REQ-002": 1},
    rule_versions={"ids:spec-1": "9f8e7d6c"},
)
PLAN = ReviewPlan(checks=[PlannedCheck(check_id="c" * 16, reason="confirmed requirement")])


def make_result(**overrides: object) -> CheckResult:
    data: dict[str, object] = {
        "check_id": "c" * 16,
        "requirement_id": "REQ-001",
        "status": "failed",
        "applicable_count": 2,
        "finding_ids": ["0123456789abcdef"],
        "diagnostics": [],
    }
    data.update(overrides)
    return CheckResult.model_validate(data)


def make_run(**overrides: object) -> ReviewRun:
    data: dict[str, object] = {
        "id": "run-0001",
        "session_id": "sess-0001",
        "status": "completed",
        "plan": PLAN,
        "plan_source": "default",
        "check_results": [make_result()],
        "input_manifest": MANIFEST,
        "created_at": T0,
        "finished_at": T1,
    }
    data.update(overrides)
    return ReviewRun.model_validate(data)


def test_failed_result_requires_findings() -> None:
    assert make_result().finding_ids == ["0123456789abcdef"]
    with pytest.raises(ValidationError, match="finding_ids"):
        make_result(status="failed", finding_ids=[])


@pytest.mark.parametrize("status", ["passed", "not_applicable", "skipped", "error"])
def test_non_failed_results_carry_no_findings(status: str) -> None:
    with pytest.raises(ValidationError, match="finding_ids"):
        make_result(status=status, finding_ids=["0123456789abcdef"], diagnostics=["x"])


def test_not_applicable_means_zero_applicable_entities() -> None:
    result = make_result(status="not_applicable", applicable_count=0, finding_ids=[])
    assert result.status == "not_applicable"
    with pytest.raises(ValidationError, match="applicable_count"):
        make_result(status="not_applicable", applicable_count=1, finding_ids=[])


def test_error_result_requires_a_diagnostic_message() -> None:
    result = make_result(
        status="error", finding_ids=[], diagnostics=["IfcTester raised ValueError"]
    )
    assert result.diagnostics == ["IfcTester raised ValueError"]
    with pytest.raises(ValidationError, match="diagnostics"):
        make_result(status="error", finding_ids=[], diagnostics=[])


def test_passed_with_zero_applicable_is_allowed_for_prohibited_specifications() -> None:
    assert make_result(status="passed", applicable_count=0, finding_ids=[]).status == "passed"


def test_statuses_outside_the_vocabulary_are_rejected() -> None:
    with pytest.raises(ValidationError):
        make_result(status="check_error", finding_ids=[])


def test_completed_run_requires_finished_at() -> None:
    assert make_run().finished_at == T1
    with pytest.raises(ValidationError, match="finished_at"):
        make_run(status="completed", finished_at=None)


@pytest.mark.parametrize("status", ["queued", "running"])
def test_active_runs_have_no_finished_at(status: str) -> None:
    assert make_run(status=status, finished_at=None).finished_at is None
    with pytest.raises(ValidationError, match="finished_at"):
        make_run(status=status, finished_at=T1)


def test_finished_at_is_not_before_created_at() -> None:
    with pytest.raises(ValidationError, match="finished_at"):
        make_run(created_at=T1, finished_at=T0)


def test_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        make_run(created_at=datetime(2026, 10, 27, 10, 0), finished_at=T1)


def test_run_aggregates_finding_ids_in_check_result_order() -> None:
    run = make_run(
        check_results=[
            make_result(check_id="1" * 16, finding_ids=["bbbbbbbbbbbbbbbb", "aaaaaaaaaaaaaaaa"]),
            make_result(check_id="2" * 16, status="passed", applicable_count=1, finding_ids=[]),
            make_result(check_id="3" * 16, finding_ids=["cccccccccccccccc"]),
        ]
    )
    assert run.finding_ids == ["bbbbbbbbbbbbbbbb", "aaaaaaaaaaaaaaaa", "cccccccccccccccc"]


def test_duplicate_check_results_are_rejected() -> None:
    with pytest.raises(ValidationError, match="check_id"):
        make_run(check_results=[make_result(), make_result()])


def test_plan_source_vocabulary() -> None:
    assert make_run(plan_source="llm").plan_source == "llm"
    with pytest.raises(ValidationError):
        make_run(plan_source="human")


def test_planned_check_carries_only_an_identifier_and_a_reason() -> None:
    assert set(PlannedCheck.model_fields) == {"check_id", "reason"}
    with pytest.raises(ValidationError):
        PlannedCheck.model_validate({"check_id": "c" * 16, "reason": "r", "params": {"x": 1}})
