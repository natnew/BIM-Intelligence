"""Provider boundary; only this package imports the OpenAI SDK (AGENTS.md §3)."""

from bim_intelligence.llm.client import (
    ChatMessage,
    Completion,
    FakeClient,
    LiveClient,
    LLMClient,
    RecordingClient,
    ReplayClient,
)
from bim_intelligence.llm.errors import LLMClientError
from bim_intelligence.llm.factory import create_budget_ledger, create_client

__all__ = [
    "ChatMessage",
    "Completion",
    "FakeClient",
    "LLMClient",
    "LLMClientError",
    "LiveClient",
    "RecordingClient",
    "ReplayClient",
    "create_budget_ledger",
    "create_client",
]
