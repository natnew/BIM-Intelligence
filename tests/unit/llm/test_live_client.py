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
from bim_intelligence.llm.errors import (
    BudgetLimitError,
    LLMContentFilterError,
    LLMMissingOutputError,
    LLMOutputError,
    LLMRefusalError,
    LLMRequestError,
    TokenLimitError,
)
from bim_intelligence.schemas import ReviewPlan


class _Completions:
    def __init__(self, response: object | Exception) -> None:
        self.response = response
        self.calls = 0
        self.requests: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.requests.append(kwargs)
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
    *,
    content: str | None = '{"checks": []}',
    model: str = "muse-spark-1.3",
    input_tokens: int = 20,
    output_tokens: int = 5,
    response_id: str = "response-id",
    finish_reason: str | None = "stop",
    reasoning_tokens: int | None = None,
    refusal: str | None = None,
    include_usage: bool = True,
) -> object:
    return SimpleNamespace(
        id=response_id,
        model=model,
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(content=content, refusal=refusal),
            )
        ],
        usage=(
            SimpleNamespace(
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                prompt_tokens_details=SimpleNamespace(cached_tokens=0),
                completion_tokens_details=(
                    SimpleNamespace(reasoning_tokens=reasoning_tokens)
                    if reasoning_tokens is not None
                    else None
                ),
            )
            if include_usage
            else None
        ),
    )


def _ledger(settings: Settings) -> BudgetLedger:
    from bim_intelligence.llm.factory import create_budget_ledger

    return create_budget_ledger(settings)


def test_live_client_uses_stubbed_sdk_and_reconciles_usage(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    sdk = _SdkClient(
        _response(
            model="muse-spark-1.3-returned",
            reasoning_tokens=3,
        )
    )
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
    assert completion.model == "muse-spark-1.3-returned"
    assert completion.response_id == "response-id"
    assert completion.provider_request_attempted is True
    assert completion.usage == TokenUsage(input_tokens=20, output_tokens=5, reasoning_tokens=3)
    assert sdk.chat.completions.calls == 1
    request = sdk.chat.completions.requests[0]
    assert request["max_completion_tokens"] == 20
    assert "max_tokens" not in request
    assert request["reasoning_effort"] == "low"
    response_format = request["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "reviewplan"
    assert response_format["json_schema"]["schema"]["required"] == ["checks"]
    assert response_format["json_schema"]["schema"]["additionalProperties"] is False
    assert "strict" not in response_format["json_schema"]
    status = _ledger(settings).status()
    assert status.request_count == 1
    assert status.spent_usd > 0
    ledger_row = json.loads((settings.data_dir / "llm" / "budget.json").read_text())["requests"][0]
    assert ledger_row["model"] == "muse-spark-1.3-returned"
    assert ledger_row["response_id"] == "response-id"
    assert ledger_row["finish_reason"] == "stop"
    assert ledger_row["output_tokens"] == 5
    assert ledger_row["reasoning_tokens"] == 3
    assert ledger_row["visible_content"] is True
    assert ledger_row["outcome"] == "success"
    assert "safe prompt" not in (settings.data_dir / "llm" / "budget.json").read_text()
    assert settings.model_api_key is not None
    assert (
        settings.model_api_key.get_secret_value()
        not in (settings.data_dir / "llm" / "budget.json").read_text()
    )


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


def test_missing_plan_field_is_schema_invalid(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    sdk = _SdkClient(_response(content="{}"))
    with pytest.raises(LLMOutputError):
        LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, sdk)).complete(
            [ChatMessage(role="user", content="safe prompt")],
            response_model=ReviewPlan,
            max_output_tokens=20,
            purpose="plan",
            run_id="run-1",
        )
    row = json.loads((settings.data_dir / "llm" / "budget.json").read_text())["requests"][0]
    assert row["outcome"] == "invalid_output"


@pytest.mark.parametrize(
    "content",
    [
        "not-json",
        '{"checks": [], "unexpected": true}',
        '{"checks": [{"check_id": "id"}]}',
        '{"checks": [{"check_id": "id", "reason": "Run.", "tool": "shell"}]}',
    ],
)
def test_live_client_rejects_malformed_or_additional_plan_fields(
    tmp_path: Path, content: str
) -> None:
    settings = _settings(tmp_path)
    sdk = _SdkClient(_response(content=content))
    with pytest.raises(LLMOutputError):
        LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, sdk)).complete(
            [ChatMessage(role="user", content="safe prompt")],
            response_model=ReviewPlan,
            max_output_tokens=20,
            purpose="plan",
            run_id="run-1",
        )
    row = json.loads((settings.data_dir / "llm" / "budget.json").read_text())["requests"][0]
    assert row["outcome"] == "invalid_output"


def test_truncated_visible_json_is_a_token_limit_failure(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    sdk = _SdkClient(
        _response(
            content='{"checks": [',
            output_tokens=2_000,
            finish_reason="length",
            include_usage=False,
        )
    )
    with pytest.raises(TokenLimitError):
        LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, sdk)).complete(
            [ChatMessage(role="user", content="safe prompt")],
            response_model=ReviewPlan,
            max_output_tokens=settings.llm_max_planning_output_tokens,
            purpose="plan",
            run_id="run-1",
        )
    row = json.loads((settings.data_dir / "llm" / "budget.json").read_text())["requests"][0]
    assert row["outcome"] == "token_limit"
    assert row["visible_content"] is True
    assert row["finish_reason"] == "length"


def test_missing_output_at_completion_limit_is_a_token_limit_failure(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    sdk = _SdkClient(
        _response(
            content=None,
            output_tokens=settings.llm_max_planning_output_tokens,
            finish_reason=None,
        )
    )
    with pytest.raises(TokenLimitError):
        LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, sdk)).complete(
            [ChatMessage(role="user", content="safe prompt")],
            response_model=ReviewPlan,
            max_output_tokens=settings.llm_max_planning_output_tokens,
            purpose="plan",
            run_id="run-1",
        )
    row = json.loads((settings.data_dir / "llm" / "budget.json").read_text())["requests"][0]
    assert row["outcome"] == "token_limit"
    assert row["visible_content"] is False


def test_missing_output_below_completion_limit_is_not_schema_invalid(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    sdk = _SdkClient(_response(content=None, output_tokens=5))
    with pytest.raises(LLMMissingOutputError):
        LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, sdk)).complete(
            [ChatMessage(role="user", content="safe prompt")],
            response_model=ReviewPlan,
            max_output_tokens=20,
            purpose="plan",
            run_id="run-1",
        )
    row = json.loads((settings.data_dir / "llm" / "budget.json").read_text())["requests"][0]
    assert row["outcome"] == "missing_output"


def test_refusal_is_safe_and_does_not_store_refusal_text(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    sdk = _SdkClient(_response(content=None, refusal="private refusal text", output_tokens=4))
    with pytest.raises(LLMRefusalError) as exc_info:
        LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, sdk)).complete(
            [ChatMessage(role="user", content="safe prompt")],
            response_model=ReviewPlan,
            max_output_tokens=20,
            purpose="plan",
            run_id="run-1",
        )
    ledger_text = (settings.data_dir / "llm" / "budget.json").read_text()
    assert "private refusal text" not in str(exc_info.value)
    assert "private refusal text" not in ledger_text
    row = json.loads(ledger_text)["requests"][0]
    assert row["outcome"] == "refused"
    assert row["visible_content"] is False


def test_content_filter_is_recorded_without_exposing_provider_content(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    sdk = _SdkClient(_response(content=None, output_tokens=4, finish_reason="content_filter"))
    with pytest.raises(LLMContentFilterError):
        LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, sdk)).complete(
            [ChatMessage(role="user", content="safe prompt")],
            response_model=ReviewPlan,
            max_output_tokens=20,
            purpose="plan",
            run_id="run-1",
        )
    row = json.loads((settings.data_dir / "llm" / "budget.json").read_text())["requests"][0]
    assert row["outcome"] == "content_filter"
    assert row["finish_reason"] == "content_filter"


def test_non_planning_requests_keep_the_500_token_cap(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    sdk = _SdkClient(_response())
    with pytest.raises(TokenLimitError):
        LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, sdk)).complete(
            [ChatMessage(role="user", content="safe prompt")],
            response_model=ReviewPlan,
            max_output_tokens=501,
            purpose="extraction",
            run_id="run-1",
        )
    assert sdk.chat.completions.calls == 0
    request_without_reasoning = _SdkClient(_response())
    LiveClient(
        settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, request_without_reasoning)
    ).complete(
        [ChatMessage(role="user", content="safe prompt")],
        response_model=ReviewPlan,
        max_output_tokens=500,
        purpose="extraction",
        run_id="run-2",
    )
    assert "reasoning_effort" not in request_without_reasoning.chat.completions.requests[0]


def test_explanation_requests_use_their_own_allowance_at_low_reasoning_effort(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    sdk = _SdkClient(_response())
    LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, sdk)).complete(
        [ChatMessage(role="user", content="safe prompt")],
        response_model=ReviewPlan,
        max_output_tokens=settings.llm_max_explanation_output_tokens,
        purpose="explanation",
        run_id="run-1",
    )
    request = sdk.chat.completions.requests[0]
    assert request["max_completion_tokens"] == 2_000
    assert request["reasoning_effort"] == "low"
    assert "max_tokens" not in request

    over_cap = _SdkClient(_response())
    with pytest.raises(TokenLimitError):
        LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, over_cap)).complete(
            [ChatMessage(role="user", content="safe prompt")],
            response_model=ReviewPlan,
            max_output_tokens=settings.llm_max_explanation_output_tokens + 1,
            purpose="explanation",
            run_id="run-2",
        )
    assert over_cap.chat.completions.calls == 0


def test_verify_009_explanation_exhaustion_is_a_token_limit_failure(tmp_path: Path) -> None:
    """Reproduce the live VERIFY-009 explanation response: length-stopped, reasoning-only."""
    settings = _settings(tmp_path)
    sdk = _SdkClient(
        _response(
            content=None,
            input_tokens=1_203,
            output_tokens=500,
            reasoning_tokens=498,
            finish_reason="length",
        )
    )
    with pytest.raises(TokenLimitError):
        LiveClient(settings, ledger=_ledger(settings), sdk_client=cast(OpenAI, sdk)).complete(
            [ChatMessage(role="user", content="safe evidence prompt " * 80)],
            response_model=ReviewPlan,
            max_output_tokens=500,
            purpose="explanation",
            run_id="run-1",
        )
    row = json.loads((settings.data_dir / "llm" / "budget.json").read_text())["requests"][0]
    assert row["outcome"] == "token_limit"
    assert row["finish_reason"] == "length"
    assert row["output_tokens"] == 500
    assert row["reasoning_tokens"] == 498
    assert row["visible_content"] is False
