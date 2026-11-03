"""An offline stand-in for the OpenAI SDK, used to drive :class:`LiveClient` without a network.

The stub records the exact keyword arguments ``chat.completions.create`` receives, so a test can
assert the real request body (model, messages, token cap, response format) that a live run
would send, while the persistent budget ledger and output validation run unmodified.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from openai import OpenAI

from bim_intelligence.config import Settings
from bim_intelligence.llm.client import LiveClient
from bim_intelligence.llm.factory import create_budget_ledger

TEST_API_KEY = "LLM_TEST_" + "x" * 24


class CapturingCompletions:
    """Stub response transport recording the exact SDK request and safe response metadata."""

    def __init__(
        self,
        content: str | None,
        *,
        input_tokens: int = 900,
        output_tokens: int = 120,
        model: str = "muse-spark-1.3",
        response_id: str = "stub-response",
        finish_reason: str | None = "stop",
        reasoning_tokens: int | None = None,
        refusal: str | None = None,
    ) -> None:
        self.content = content
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.model = model
        self.response_id = response_id
        self.finish_reason = finish_reason
        self.reasoning_tokens = reasoning_tokens
        self.refusal = refusal
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> object:
        self.requests.append(kwargs)
        completion_details = (
            SimpleNamespace(reasoning_tokens=self.reasoning_tokens)
            if self.reasoning_tokens is not None
            else None
        )
        return SimpleNamespace(
            id=self.response_id,
            model=self.model,
            choices=[
                SimpleNamespace(
                    finish_reason=self.finish_reason,
                    message=SimpleNamespace(content=self.content, refusal=self.refusal),
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=self.input_tokens,
                completion_tokens=self.output_tokens,
                prompt_tokens_details=SimpleNamespace(cached_tokens=0),
                completion_tokens_details=completion_details,
            ),
        )


def live_settings(tmp_path: Path, **overrides: object) -> Settings:
    """Live-mode settings with a placeholder key and an isolated budget ledger directory."""
    values: dict[str, object] = {
        "llm_mode": "live",
        "allow_live_llm": True,
        "model_api_key": TEST_API_KEY,
        "data_dir": tmp_path / "live-data",
    }
    values.update(overrides)
    return Settings.model_validate(values)


def stub_live_client(settings: Settings, completions: CapturingCompletions) -> LiveClient:
    """A real :class:`LiveClient` and budget ledger whose SDK transport is ``completions``."""
    sdk = cast(OpenAI, SimpleNamespace(chat=SimpleNamespace(completions=completions)))
    return LiveClient(settings, ledger=create_budget_ledger(settings), sdk_client=sdk)
