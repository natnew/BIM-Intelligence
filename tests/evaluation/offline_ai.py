"""Small deterministic checks of the T-5 offline client and safety contracts."""

from __future__ import annotations

import json
import socket
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from bim_intelligence.bim import build_index, open_ifc
from bim_intelligence.config import LLMMode, Settings
from bim_intelligence.llm.client import (
    ChatMessage,
    FakeClient,
    RecordingClient,
    ReplayClient,
)
from bim_intelligence.orchestration.planner import PlanViolation, propose_plan
from bim_intelligence.reporting.explanations import explain_finding
from bim_intelligence.schemas import (
    CheckSpec,
    ElementRef,
    Finding,
    ModelSummary,
    PlannedCheck,
    Requirement,
    ReviewPlan,
)
from bim_intelligence.validation import classification_consistency_check
from fixtures.make_minimal_ifc import GLOBAL_IDS, IFC_PATH


def evaluate_offline_ai() -> dict[str, Any]:
    """Measure offline contract outcomes without constructing a live client."""
    network_attempts: list[str] = []

    def blocked_connect(_socket: socket.socket, address: Any) -> None:
        network_attempts.append(repr(address))
        raise AssertionError(f"Network access is forbidden in offline evaluation: {address!r}")

    def blocked_connect_ex(_socket: socket.socket, address: Any) -> int:
        network_attempts.append(repr(address))
        raise AssertionError(f"Network access is forbidden in offline evaluation: {address!r}")

    with (
        patch.object(socket.socket, "connect", blocked_connect),
        patch.object(socket.socket, "connect_ex", blocked_connect_ex),
    ):
        checks = _evaluate_contract()
    return {
        "classification": "offline Fake/Replay contract checks; not live Muse Spark performance",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "network_calls": len(network_attempts),
        "live_api_calls": 0,
        "live_spend_usd": "0",
    }


def _evaluate_contract() -> dict[str, bool]:
    check = classification_consistency_check()
    requirement = _requirement(check)
    summary = ModelSummary(
        ifc_schema="IFC4",
        model_hash="0" * 64,
        counts={"IfcWall": 1},
        storeys=[],
    )
    settings = Settings(_env_file=None, llm_mode=LLMMode.OFF)
    valid_plan_client = FakeClient(
        [{"checks": [{"check_id": check.id, "reason": "Check classification consistency."}]}]
    )
    valid_plan = propose_plan(
        valid_plan_client,
        objective="Check wall classifications.",
        summary=summary,
        requirements=[requirement],
        settings=settings,
        run_id="offline-plan",
    )
    plan_schema_and_selection = (
        valid_plan.plan
        == ReviewPlan(
            checks=[PlannedCheck(check_id=check.id, reason="Check classification consistency.")]
        )
        and valid_plan_client.calls == 1
    )

    unconfirmed_rejected = _plan_rejected(
        {"checks": [{"check_id": check.id, "reason": "Run an unconfirmed check."}]},
        [_requirement(check, status="proposed")],
        settings,
    )
    unknown_rejected = _plan_rejected(
        {"checks": [{"check_id": "unknown-check", "reason": "Unknown."}]},
        [requirement],
        settings,
    )
    duplicate_rejected = _plan_rejected(
        {
            "checks": [
                {"check_id": check.id, "reason": "First."},
                {"check_id": check.id, "reason": "Duplicate."},
            ]
        },
        [requirement],
        settings,
    )
    cap_rejected = _cap_rejected(check, requirement, settings)

    finding, index = _finding_and_index()
    invalid_response: dict[str, object] = {
        "finding_id": finding.id,
        "summary": "GlobalId 0000000000000000000000 has 90 mm.",
        "probable_cause": "The check failed.",
        "corrective_action": "Replace the value with 90 mm.",
        "citations": [],
    }
    fallback_a = explain_finding(
        finding,
        requirement,
        index,
        FakeClient([invalid_response]),
        run_id="offline-explanation",
    )
    fallback_b = explain_finding(
        finding,
        requirement,
        index,
        FakeClient([invalid_response]),
        run_id="offline-explanation",
    )
    serialized_a = json.dumps(
        fallback_a.model_dump(mode="json"), ensure_ascii=False, sort_keys=True
    )
    serialized_b = json.dumps(
        fallback_b.model_dump(mode="json"), ensure_ascii=False, sort_keys=True
    )
    grounding_rejected = (
        fallback_a.source == "deterministic_template" and fallback_a.grounding_status == "fallback"
    )
    deterministic_fallback = serialized_a == serialized_b
    replay_repeatable = _replay_repeatable(valid_plan.plan)

    return {
        "plan_schema_valid_and_selection_registered": plan_schema_and_selection,
        "unconfirmed_check_rejected": unconfirmed_rejected,
        "unknown_check_rejected": unknown_rejected,
        "duplicate_check_rejected": duplicate_rejected,
        "execution_cap_enforced": cap_rejected,
        "grounding_violation_rejected": grounding_rejected,
        "deterministic_explanation_fallback": deterministic_fallback,
        "replayed_response_repeatable": replay_repeatable,
        "live_client_not_constructed": True,
    }


def _plan_rejected(
    response: dict[str, object],
    requirements: list[Requirement],
    settings: Settings,
) -> bool:
    try:
        propose_plan(
            FakeClient([response]),
            objective="Evaluate a bounded review.",
            summary=ModelSummary(
                ifc_schema="IFC4",
                model_hash="0" * 64,
                counts={"IfcWall": 1},
                storeys=[],
            ),
            requirements=requirements,
            settings=settings,
            run_id="offline-rejection",
        )
    except PlanViolation:
        return True
    return False


def _cap_rejected(check: CheckSpec, requirement: Requirement, settings: Settings) -> bool:
    second_check = CheckSpec(
        kind="native",
        rule_id="test.offline_cap",
        rule_version="1.0.0",
        params={},
    )
    second_requirement = _requirement(second_check, id="REQ-OFFLINE-2")
    response: dict[str, object] = {
        "checks": [
            {"check_id": check.id, "reason": "First."},
            {"check_id": second_check.id, "reason": "Exceeds cap."},
        ]
    }
    try:
        propose_plan(
            FakeClient([response]),
            objective="Evaluate the execution cap.",
            summary=ModelSummary(
                ifc_schema="IFC4",
                model_hash="0" * 64,
                counts={"IfcWall": 1},
                storeys=[],
            ),
            requirements=[requirement, second_requirement],
            settings=settings.model_copy(
                update={"max_plan_checks": 1, "max_tool_calls_per_run": 1}
            ),
            run_id="offline-cap",
        )
    except PlanViolation:
        return True
    return False


def _replay_repeatable(expected: ReviewPlan) -> bool:
    response: dict[str, object] = {
        "checks": [{"check_id": item.check_id, "reason": item.reason} for item in expected.checks]
    }
    messages = [
        ChatMessage(role="system", content="Return the provided plan."),
        ChatMessage(role="user", content="Select a check."),
    ]
    with tempfile.TemporaryDirectory(prefix="bimi-offline-replay-") as directory:
        recordings = Path(directory)
        recorder = RecordingClient(FakeClient([response]), recordings)
        recorded = recorder.complete(
            messages,
            response_model=ReviewPlan,
            max_output_tokens=64,
            purpose="plan",
            run_id="record",
        )
        replay_a = ReplayClient(recordings).complete(
            messages,
            response_model=ReviewPlan,
            max_output_tokens=64,
            purpose="plan",
            run_id="replay-a",
        )
        replay_b = ReplayClient(recordings).complete(
            messages,
            response_model=ReviewPlan,
            max_output_tokens=64,
            purpose="plan",
            run_id="replay-b",
        )
    return (
        recorded.value == expected
        and replay_a.value == replay_b.value == expected
        and replay_a.model == replay_b.model == "fake-model"
    )


def _finding_and_index() -> tuple[Finding, Any]:
    model = open_ifc(IFC_PATH)
    index = build_index(model, model_hash="0" * 64)
    check = classification_consistency_check()
    element = index.by_global_id(GLOBAL_IDS["W-002"]).ref
    finding = Finding(
        check_id=check.id,
        requirement_id="REQ-OFFLINE",
        rule_id=check.rule_id,
        rule_version=check.rule_version,
        facet_index=0,
        severity="error",
        category="classification_inconsistent",
        elements=[ElementRef.model_validate(element.model_dump())],
        observed="'W-002' uses an incorrect classification.",
        expected="The classified wall type and occurrence must agree.",
        method="native",
    )
    return finding, index


def _requirement(
    check: CheckSpec, *, status: str = "confirmed", id: str | None = None
) -> Requirement:
    confirmed = status == "confirmed"
    return Requirement(
        id=id or f"REQ-{check.id[:8]}",
        title="Check classification consistency",
        statement="Every occurrence matches its classified type.",
        origin="builtin",
        check=check,
        status=status,
        revision=1,
        confirmed_revision=1 if confirmed else None,
    )
