from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import httpx
import pytest
from openai import APITimeoutError, OpenAI

from bim_intelligence.config import Settings
from bim_intelligence.llm.budget import BudgetLedger, TokenUsage
from bim_intelligence.llm.client import ChatMessage, LiveClient
from bim_intelligence.llm.errors import BudgetLimitError, LLMRequestError
from bim_intelligence.schemas import ReviewPlan


class _Completions:
    def __init__(self, response: object | Exception) -> None:
        self.response = response
        self.calls = 0

    def create(self, **kwargs: object) -> object:
        del kwargs
        self.calls += 1
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class _SdkClient:
    def __init__(self, response: object | Exception) -> None:
        self.chat = SimpleNamespace(completions=_Completions(response))


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "llm_mode": "live",
        "allow_live_llm": True,
        "model_api_key": "LLM_TEST_" + "x" * 24,
        "data_dir": tmp_path / "data",
    }
    values.update(overrides)
    return Settings.model_validate(values)


def _response(
    *, content: str = '{"checks": []}', input_tokens: int = 20, output_tokens: int = 5
) -> object:
    return SimpleNamespace(
        id="response-id",
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            prompt_tokens_details=SimpleNamespace(cached_tokens=0),
        ),
    )


def _ledger(settings: Settings) -> BudgetLedger:
    from bim_intelligence.llm.factory import create_budget_ledger

    return create_budget_ledger(settings)


def test_live_client_uses_stubbed_sdk_and_reconciles_usage(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    sdk = _SdkClient(_response())
    completion = LiveClient(
        settings,
        ledger=_ledger(settings),
        sdk_client=cast(OpenAI, sdk),
    ).complete(
        [ChatMessage(role="user", content="safe prompt")],
        response_model=ReviewPlan,
        max_output_tokens=20,
        purpose="plan",
        run_id="run-1",
    )

    assert completion.value == ReviewPlan(checks=[])
    assert completion.usage == TokenUsage(input_tokens=20, output_tokens=5)
    assert sdk.chat.completions.calls == 1
    status = _ledger(settings).status()
    assert status.request_count == 1
    assert status.spent_usd > 0


def test_timeout_is_sanitised_and_maximum_reservation_is_charged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    settings = _settings(tmp_path)
    assert settings.model_api_key is not None
    secret_placeholder = settings.model_api_key.get_secret_value()
    sdk = _SdkClient(
        APITimeoutError(request=httpx.Request("POST", "https://api.meta.ai/v1/chat/completions"))
    )
    with pytest.raises(LLMRequestError) as exc_info:
        LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, sdk)).complete(
            [ChatMessage(role="user", content="safe prompt")],
            response_model=ReviewPlan,
            max_output_tokens=20,
            purpose="plan",
            run_id="run-1",
        )

    assert secret_placeholder not in str(exc_info.value)
    assert secret_placeholder not in caplog.text
    assert sdk.chat.completions.calls == 1
    ledger_state = json.loads((settings.data_dir / "llm" / "budget.json").read_text())
    assert ledger_state["requests"][0]["outcome"] == "provider_error:APITimeoutError"
    assert (
        ledger_state["requests"][0]["charged_cost_usd"]
        == ledger_state["requests"][0]["estimated_cost_usd"]
    )


def test_budget_exhaustion_precedes_sdk_request(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        llm_project_budget_usd="0.00001",
        llm_max_run_budget_usd="0.00001",
        llm_max_call_budget_usd="0.00001",
    )
    sdk = _SdkClient(_response())
    with pytest.raises(BudgetLimitError):
        LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, sdk)).complete(
            [ChatMessage(role="user", content="safe prompt")],
            response_model=ReviewPlan,
            max_output_tokens=20,
            purpose="plan",
            run_id="run-1",
        )
    assert sdk.chat.completions.calls == 0
