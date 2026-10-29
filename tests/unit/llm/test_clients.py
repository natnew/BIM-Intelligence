from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from bim_intelligence.llm.budget import TokenUsage
from bim_intelligence.llm.client import (
    ChatMessage,
    FakeClient,
    LLMClient,
    RecordingClient,
    ReplayClient,
)
from bim_intelligence.llm.errors import LLMOutputError, ReplayMismatchError
from bim_intelligence.schemas import ReviewPlan


class _TextResponse(BaseModel):
    message: str


def _complete(client: LLMClient) -> ReviewPlan:
    return client.complete(
        [ChatMessage(role="user", content="safe prompt")],
        response_model=ReviewPlan,
        max_output_tokens=20,
        purpose="plan",
        run_id="run-1",
    ).value


def test_fake_client_validates_structured_output_without_network() -> None:
    fake = FakeClient([{"checks": []}])
    assert _complete(fake) == ReviewPlan(checks=[])
    assert fake.calls == 1


def test_fake_client_rejects_invalid_structured_output() -> None:
    fake = FakeClient([{"checks": [], "unexpected": "tool execution"}])
    with pytest.raises(LLMOutputError):
        _complete(fake)


def test_recording_omits_prompts_and_redacts_key_shaped_output(tmp_path: Path) -> None:
    key_shaped_value = "LLM_" + "TEST_" + "x" * 24
    client = RecordingClient(
        FakeClient([{"message": key_shaped_value}]),
        tmp_path,
    )
    client.complete(
        [ChatMessage(role="user", content="private prompt")],
        response_model=_TextResponse,
        max_output_tokens=20,
        purpose="test",
        run_id="run-1",
    )
    serialized = next(tmp_path.glob("*.json")).read_text(encoding="utf-8")
    assert key_shaped_value not in serialized
    assert "[redacted]" in serialized
    assert "private prompt" not in serialized


def test_recording_and_replay_work_offline(tmp_path: Path) -> None:
    recorded = RecordingClient(FakeClient([{"checks": []}]), tmp_path)
    expected = _complete(recorded)
    assert expected == _complete(ReplayClient(tmp_path))
    payload = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    assert "safe prompt" not in json.dumps(payload)
    assert payload["request_hash"]


def test_replay_rejects_a_different_prompt(tmp_path: Path) -> None:
    _complete(RecordingClient(FakeClient([{"checks": []}]), tmp_path))
    replay = ReplayClient(tmp_path)
    with pytest.raises(ReplayMismatchError, match="does not match"):
        replay.complete(
            [ChatMessage(role="user", content="different prompt")],
            response_model=ReviewPlan,
            max_output_tokens=20,
            purpose="plan",
            run_id="run-1",
        )


def test_fake_default_usage_is_zero_cost_metadata() -> None:
    completion = FakeClient([{"checks": []}]).complete(
        [ChatMessage(role="user", content="")],
        response_model=ReviewPlan,
        max_output_tokens=20,
        purpose="plan",
        run_id="run-1",
    )
    assert completion.usage == TokenUsage(input_tokens=0, output_tokens=0)
