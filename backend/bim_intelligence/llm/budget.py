"""Persistent, concurrency-safe application spending controls for live model requests."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

from bim_intelligence.llm.errors import BudgetLimitError, BudgetStateError
from bim_intelligence.store.locking import FileLock

_ALLOWED_LEDGER_OUTCOMES = frozenset(
    {
        "reserved",
        "usage_unavailable",
        "timeout",
        "missing_output",
        "usage_limit_exceeded",
        "invalid_output",
        "success",
    }
)


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0

    def __post_init__(self) -> None:
        if min(self.input_tokens, self.output_tokens, self.cached_input_tokens) < 0:
            raise ValueError("Token counts must not be negative.")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("Cached input tokens cannot exceed total input tokens.")


@dataclass(frozen=True)
class BudgetReservation:
    request_id: str
    run_id: str
    estimated_input_tokens: int
    max_output_tokens: int
    estimated_cost_usd: Decimal


@dataclass(frozen=True)
class BudgetStatus:
    project_budget_usd: Decimal
    spent_usd: Decimal
    reserved_usd: Decimal
    remaining_usd: Decimal
    request_count: int


class BudgetLedger:
    """Atomic JSON ledger with a cross-process file lock and conservative reservations."""

    def __init__(
        self,
        path: Path,
        *,
        project_budget_usd: Decimal,
        run_budget_usd: Decimal,
        call_budget_usd: Decimal,
        input_price_per_m: Decimal,
        cached_input_price_per_m: Decimal,
        output_price_per_m: Decimal,
        max_calls_per_run: int,
        max_input_tokens: int,
        max_output_tokens: int,
    ) -> None:
        self.path = path
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self.project_budget_usd = project_budget_usd
        self.run_budget_usd = run_budget_usd
        self.call_budget_usd = call_budget_usd
        self.input_price_per_m = input_price_per_m
        self.cached_input_price_per_m = cached_input_price_per_m
        self.output_price_per_m = output_price_per_m
        self.max_calls_per_run = max_calls_per_run
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        return (
            Decimal(input_tokens) * self.input_price_per_m
            + Decimal(output_tokens) * self.output_price_per_m
        ) / Decimal(1_000_000)

    def reserve(
        self,
        *,
        request_id: str,
        run_id: str,
        estimated_input_tokens: int,
        max_output_tokens: int,
    ) -> BudgetReservation:
        if estimated_input_tokens < 0 or estimated_input_tokens > self.max_input_tokens:
            raise BudgetLimitError(
                f"Estimated input exceeds the {self.max_input_tokens}-token per-call limit."
            )
        if max_output_tokens < 1 or max_output_tokens > self.max_output_tokens:
            raise BudgetLimitError(
                f"Output exceeds the {self.max_output_tokens}-token per-call limit."
            )
        estimated_cost = self.estimate_cost(estimated_input_tokens, max_output_tokens)
        if estimated_cost > self.call_budget_usd:
            raise BudgetLimitError("Request would exceed the per-call budget.")
        reservation = BudgetReservation(
            request_id=request_id,
            run_id=run_id,
            estimated_input_tokens=estimated_input_tokens,
            max_output_tokens=max_output_tokens,
            estimated_cost_usd=estimated_cost,
        )
        with self._locked_state() as state:
            requests = self._requests(state)
            if any(row.get("request_id") == request_id for row in requests):
                raise BudgetStateError("Duplicate budget request id.")
            run_requests = [row for row in requests if row.get("run_id") == run_id]
            if len(run_requests) >= self.max_calls_per_run:
                raise BudgetLimitError(
                    f"Review has reached the {self.max_calls_per_run}-call limit."
                )
            run_committed = sum(
                (self._charged_or_reserved(row) for row in run_requests), Decimal(0)
            )
            if run_committed + estimated_cost > self.run_budget_usd:
                raise BudgetLimitError("Request would exceed the per-review budget.")
            project_committed = sum(
                (self._charged_or_reserved(row) for row in requests), Decimal(0)
            )
            if project_committed + estimated_cost > self.project_budget_usd:
                raise BudgetLimitError("Request would exceed the cumulative project budget.")
            requests.append(
                {
                    "request_id": request_id,
                    "run_id": run_id,
                    "estimated_input_tokens": estimated_input_tokens,
                    "max_output_tokens": max_output_tokens,
                    "estimated_cost_usd": str(estimated_cost),
                    "charged_cost_usd": None,
                    "input_tokens": None,
                    "output_tokens": None,
                    "cached_input_tokens": None,
                    "actual_cost_usd": None,
                    "model": None,
                    "outcome": "reserved",
                }
            )
            self._write_state(state)
        return reservation

    def settle(
        self,
        reservation: BudgetReservation,
        *,
        usage: TokenUsage | None,
        model: str,
        outcome: str,
    ) -> Decimal:
        with self._locked_state() as state:
            row = self._find_request(state, reservation.request_id)
            if row.get("outcome") != "reserved":
                raise BudgetStateError("Budget reservation is not pending.")
            actual_cost: Decimal | None = None
            if usage is not None:
                actual_cost = (
                    Decimal(usage.input_tokens - usage.cached_input_tokens) * self.input_price_per_m
                    + Decimal(usage.cached_input_tokens) * self.cached_input_price_per_m
                    + Decimal(usage.output_tokens) * self.output_price_per_m
                ) / Decimal(1_000_000)
                row["input_tokens"] = usage.input_tokens
                row["output_tokens"] = usage.output_tokens
                row["cached_input_tokens"] = usage.cached_input_tokens
                row["actual_cost_usd"] = str(actual_cost)
            row["charged_cost_usd"] = str(
                actual_cost if actual_cost is not None else reservation.estimated_cost_usd
            )
            row["model"] = model
            row["outcome"] = outcome
            self._write_state(state)
        if actual_cost is not None and actual_cost > reservation.estimated_cost_usd:
            raise BudgetLimitError(
                "Provider usage exceeded the reserved estimate; further requests are blocked."
            )
        return actual_cost if actual_cost is not None else reservation.estimated_cost_usd

    def status(self) -> BudgetStatus:
        with self._locked_state() as state:
            requests = self._requests(state)
            spent = sum(
                (
                    Decimal(str(row["charged_cost_usd"]))
                    for row in requests
                    if row.get("charged_cost_usd") is not None
                ),
                Decimal(0),
            )
            reserved = sum(
                (
                    Decimal(str(row["estimated_cost_usd"]))
                    for row in requests
                    if row.get("outcome") == "reserved"
                ),
                Decimal(0),
            )
            return BudgetStatus(
                project_budget_usd=self.project_budget_usd,
                spent_usd=spent,
                reserved_usd=reserved,
                remaining_usd=max(Decimal(0), self.project_budget_usd - spent - reserved),
                request_count=len(requests),
            )

    def _locked_state(self) -> _LockedState:
        return _LockedState(self)

    def _read_state(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "requests": []}
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise BudgetStateError(
                "Budget state is unreadable; live requests are disabled."
            ) from exc
        if (
            not isinstance(state, dict)
            or state.get("version") != 1
            or not isinstance(state.get("requests"), list)
        ):
            raise BudgetStateError(
                "Budget state has an unsupported shape; live requests are disabled."
            )
        seen_ids: set[str] = set()
        for row in state["requests"]:
            if (
                not isinstance(row, dict)
                or set(row)
                != {
                    "request_id",
                    "run_id",
                    "estimated_input_tokens",
                    "max_output_tokens",
                    "estimated_cost_usd",
                    "charged_cost_usd",
                    "input_tokens",
                    "output_tokens",
                    "cached_input_tokens",
                    "actual_cost_usd",
                    "model",
                    "outcome",
                }
                or not isinstance(row.get("request_id"), str)
                or not row["request_id"]
                or row["request_id"] in seen_ids
                or not isinstance(row.get("run_id"), str)
                or not row["run_id"]
                or not isinstance(row.get("estimated_cost_usd"), str)
                or not isinstance(row.get("outcome"), str)
                or (
                    row["outcome"] not in _ALLOWED_LEDGER_OUTCOMES
                    and not row["outcome"].startswith("provider_error:")
                )
            ):
                raise BudgetStateError("Budget state is invalid; live requests are disabled.")
            seen_ids.add(row["request_id"])
            try:
                estimate = Decimal(row["estimated_cost_usd"])
                charged = row.get("charged_cost_usd")
                if charged is not None:
                    charged_cost = Decimal(str(charged))
                    if not charged_cost.is_finite() or charged_cost < 0:
                        raise InvalidOperation
                if not estimate.is_finite() or estimate < 0:
                    raise InvalidOperation
                if row["outcome"] == "reserved" and charged is not None:
                    raise InvalidOperation
                if row["outcome"] != "reserved" and charged is None:
                    raise InvalidOperation
                estimated_input = row.get("estimated_input_tokens")
                max_output = row.get("max_output_tokens")
                if (
                    isinstance(estimated_input, bool)
                    or not isinstance(estimated_input, int)
                    or estimated_input < 0
                    or estimated_input > self.max_input_tokens
                    or isinstance(max_output, bool)
                    or not isinstance(max_output, int)
                    or max_output < 1
                    or max_output > self.max_output_tokens
                ):
                    raise InvalidOperation
                for token_key in ("input_tokens", "output_tokens", "cached_input_tokens"):
                    token_count = row.get(token_key)
                    if token_count is not None and (
                        isinstance(token_count, bool)
                        or not isinstance(token_count, int)
                        or token_count < 0
                    ):
                        raise InvalidOperation
                cached_tokens = row.get("cached_input_tokens")
                input_tokens = row.get("input_tokens")
                if (
                    cached_tokens is not None
                    and input_tokens is not None
                    and cached_tokens > input_tokens
                ):
                    raise InvalidOperation
                actual_cost = row.get("actual_cost_usd")
                if actual_cost is not None:
                    actual_cost_decimal = Decimal(str(actual_cost))
                    if not actual_cost_decimal.is_finite() or actual_cost_decimal < 0:
                        raise InvalidOperation
                if row["outcome"] == "reserved" and any(
                    row.get(key) is not None
                    for key in (
                        "input_tokens",
                        "output_tokens",
                        "cached_input_tokens",
                        "actual_cost_usd",
                        "model",
                    )
                ):
                    raise InvalidOperation
                if row.get("model") is not None and not isinstance(row["model"], str):
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                raise BudgetStateError(
                    "Budget state is invalid; live requests are disabled."
                ) from None
        return state

    def _write_state(self, state: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
            with temporary.open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(state, handle, sort_keys=True, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            raise BudgetStateError(
                "Budget state could not be persisted; live requests are disabled."
            ) from exc

    @staticmethod
    def _requests(state: dict[str, Any]) -> list[dict[str, Any]]:
        requests = state.get("requests")
        if not isinstance(requests, list) or any(not isinstance(row, dict) for row in requests):
            raise BudgetStateError("Budget state is invalid; live requests are disabled.")
        return cast(list[dict[str, Any]], requests)

    @staticmethod
    def _charged_or_reserved(row: dict[str, Any]) -> Decimal:
        amount = row.get("charged_cost_usd")
        if amount is not None:
            return Decimal(str(amount))
        return Decimal(str(row["estimated_cost_usd"]))

    @staticmethod
    def _find_request(state: dict[str, Any], request_id: str) -> dict[str, Any]:
        for row in BudgetLedger._requests(state):
            if row.get("request_id") == request_id:
                return row
        raise BudgetStateError("Budget reservation is missing.")


class _LockedState:
    def __init__(self, ledger: BudgetLedger) -> None:
        self.ledger = ledger
        self.lock: FileLock | None = None
        self.state: dict[str, Any] | None = None

    def __enter__(self) -> dict[str, Any]:
        try:
            self.ledger.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self.lock = FileLock(self.ledger.lock_path)
            self.lock.__enter__()
        except (OSError, BlockingIOError) as exc:
            raise BudgetStateError(
                "Budget accounting lock is unavailable; live requests are disabled."
            ) from exc
        try:
            self.state = self.ledger._read_state()
        except Exception:
            self.lock.__exit__(None, None, None)
            raise
        return self.state

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.lock is not None:
            self.lock.__exit__(None, None, None)
