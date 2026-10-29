from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pytest

from bim_intelligence.llm.budget import (
    BudgetLedger,
    TokenUsage,
)
from bim_intelligence.llm.errors import BudgetLimitError, BudgetStateError


def _ledger(path: Path, *, project: str = "0.02", call: str = "0.01") -> BudgetLedger:
    return BudgetLedger(
        path,
        project_budget_usd=Decimal(project),
        run_budget_usd=Decimal("0.02"),
        call_budget_usd=Decimal(call),
        input_price_per_m=Decimal("1.25"),
        cached_input_price_per_m=Decimal("0.15"),
        output_price_per_m=Decimal("4.25"),
        max_calls_per_run=2,
        max_input_tokens=8_000,
        max_output_tokens=500,
    )


def test_rejects_worst_case_request_before_reserving(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path / "ledger.json")
    with pytest.raises(BudgetLimitError, match="call budget"):
        ledger.reserve(
            request_id="request-1",
            run_id="run-1",
            estimated_input_tokens=8_000,
            max_output_tokens=500,
        )
    assert ledger.status().request_count == 0


def test_persists_spend_and_request_metadata(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    ledger = _ledger(path)
    reservation = ledger.reserve(
        request_id="request-1",
        run_id="run-1",
        estimated_input_tokens=1_000,
        max_output_tokens=100,
    )
    ledger.settle(
        reservation,
        usage=TokenUsage(input_tokens=800, output_tokens=50, cached_input_tokens=100),
        model="muse-spark-1.3",
        outcome="success",
    )

    restarted = _ledger(path)
    status = restarted.status()
    assert status.request_count == 1
    assert float(status.spent_usd) == pytest.approx(0.0011025)
    assert float(status.remaining_usd) == pytest.approx(0.0188975)
    raw = path.read_text(encoding="utf-8")
    assert "private prompt" not in raw
    assert "MODEL_API_KEY" not in raw


def test_unknown_usage_keeps_maximum_reservation_as_spend(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path / "ledger.json")
    reservation = ledger.reserve(
        request_id="request-1",
        run_id="run-1",
        estimated_input_tokens=1_000,
        max_output_tokens=100,
    )
    ledger.settle(
        reservation,
        usage=None,
        model="muse-spark-1.3",
        outcome="timeout",
    )
    assert float(ledger.status().spent_usd) == pytest.approx(float(reservation.estimated_cost_usd))


def test_enforces_two_calls_per_review(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path / "ledger.json")
    for index in range(2):
        reservation = ledger.reserve(
            request_id=f"request-{index}",
            run_id="run-1",
            estimated_input_tokens=1,
            max_output_tokens=1,
        )
        ledger.settle(
            reservation,
            usage=TokenUsage(input_tokens=1, output_tokens=1),
            model="muse-spark-1.3",
            outcome="success",
        )
    with pytest.raises(BudgetLimitError, match="call limit"):
        ledger.reserve(
            request_id="request-3",
            run_id="run-1",
            estimated_input_tokens=1,
            max_output_tokens=1,
        )


def test_concurrent_reservations_cannot_overspend_remaining_budget(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path / "ledger.json", project="0.00001", call="0.00001")

    def reserve(index: int) -> bool:
        try:
            ledger.reserve(
                request_id=f"request-{index}",
                run_id=f"run-{index}",
                estimated_input_tokens=1,
                max_output_tokens=1,
            )
        except (BudgetLimitError, BudgetStateError):
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(reserve, range(2)))
    assert sorted(outcomes) == [False, True]
    assert float(ledger.status().reserved_usd) == pytest.approx(0.0000055)


def test_corrupt_budget_state_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    path.write_text("{", encoding="utf-8")
    ledger = _ledger(path)
    with pytest.raises(BudgetStateError):
        ledger.reserve(
            request_id="request-1",
            run_id="run-1",
            estimated_input_tokens=1,
            max_output_tokens=1,
        )


def test_rejects_insufficient_project_allowance(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path / "ledger.json", project="0.000005", call="0.00001")
    with pytest.raises(BudgetLimitError, match="project budget"):
        ledger.reserve(
            request_id="request-1",
            run_id="run-1",
            estimated_input_tokens=1,
            max_output_tokens=1,
        )
