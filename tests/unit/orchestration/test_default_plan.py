"""Default plan: every executable requirement, once per check, in requirement order (FR-REQ-07)."""

from __future__ import annotations

from datetime import datetime, timezone

from bim_intelligence.orchestration import default_plan
from bim_intelligence.schemas import CheckSpec, Requirement, RequirementStatus

NOW = datetime(2026, 10, 29, 9, 0, tzinfo=timezone.utc)


def _requirement(req_id: str, name: str, *, status: RequirementStatus = "confirmed") -> Requirement:
    check = CheckSpec(
        kind="ids",
        rule_id=f"ids:{name}",
        rule_version="v1",
        ids_specification=f'<specification name="{name}"/>',
    )
    confirmed = status == "confirmed"
    return Requirement(
        id=req_id,
        title=name,
        statement=name,
        origin="ids",
        check=check,
        status=status,
        revision=1 if confirmed else 2,
        confirmed_revision=1,
        confirmed_by="ids-import" if confirmed else None,
        confirmed_at=NOW if confirmed else None,
    )


def test_plan_lists_each_executable_requirement_once() -> None:
    a, b = _requirement("REQ-001", "a"), _requirement("REQ-002", "b")
    plan, by_check = default_plan([a, b])
    assert [item.check_id for item in plan.checks] == [a.check.id, b.check.id]
    assert all(item.reason for item in plan.checks)
    assert by_check == {a.check.id: a, b.check.id: b}


def test_unconfirmed_and_edited_requirements_are_never_planned() -> None:
    plan, by_check = default_plan(
        [_requirement("REQ-001", "a"), _requirement("REQ-002", "b", status="edited")]
    )
    assert [by_check[item.check_id].id for item in plan.checks] == ["REQ-001"]


def test_identical_checks_from_different_requirements_run_once() -> None:
    first, duplicate = _requirement("REQ-001", "same"), _requirement("REQ-002", "same")
    assert first.check.id == duplicate.check.id
    plan, by_check = default_plan([duplicate, first])
    assert len(plan.checks) == 1
    # Requirement order, not input order, decides which requirement the check is attributed to.
    assert by_check[plan.checks[0].check_id].id == "REQ-001"


def test_empty_input_gives_an_empty_plan() -> None:
    plan, by_check = default_plan([])
    assert plan.checks == [] and by_check == {}
