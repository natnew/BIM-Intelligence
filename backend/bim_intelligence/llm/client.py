"""Typed, offline-first clients for the OpenAI-compatible Meta Model API."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Literal, Protocol, TypeVar

from openai import APIError, OpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params.response_format_json_schema import ResponseFormatJSONSchema
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from bim_intelligence.config import LLMMode, Settings
from bim_intelligence.llm.budget import BudgetLedger, BudgetReservation, TokenUsage
from bim_intelligence.llm.errors import (
    BudgetStateError,
    LLMClientError,
    LLMContentFilterError,
    LLMMissingOutputError,
    LLMOutputError,
    LLMRefusalError,
    LLMRequestError,
    ReplayMismatchError,
    TokenLimitError,
)
from bim_intelligence.schemas.canonical import canonical_json
from bim_intelligence.schemas.runs import ReviewPlan
from bim_intelligence.store.locking import FileLock

logger = logging.getLogger(__name__)
_MODEL_KEY_PATTERN = re.compile(r"\b(?:LLM_[A-Za-z0-9_-]{8,}|sk-[A-Za-z0-9_-]{16,})\b")
_SAFE_METADATA_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_SAFE_FINISH_REASON = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")
# Muse Spark documents ``low`` reasoning effort and rejects ``none``; structured planning and
# explanation requests use it so reasoning tokens do not exhaust the completion allowance.
_LOW_REASONING_PURPOSES = frozenset({"plan", "explanation"})
T = TypeVar("T", bound=BaseModel)


class ChatMessage(BaseModel):
    """A provider message; prompts and completions never enter the budget ledger."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["system", "user"]
    content: str


class TokenUsageModel(BaseModel):
    """Typed provider usage details used in client results and sanitized recordings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)


@dataclass(frozen=True)
class _ResponseMetadata:
    model: str
    response_id: str | None
    finish_reason: str | None
    visible_content: bool | None
    refused: bool


@dataclass(frozen=True)
class Completion(Generic[T]):
    value: T
    usage: TokenUsage
    model: str
    response_id: str | None = None
    provider_request_attempted: bool = False


class LLMClient(Protocol):
    """One typed completion interface implemented by offline and live clients."""

    @property
    def mode(self) -> LLMMode: ...

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_model: type[T],
        max_output_tokens: int,
        purpose: str,
        run_id: str,
    ) -> Completion[T]: ...


class FakeClient:
    """In-memory deterministic test client. It has no network or filesystem access."""

    def __init__(
        self,
        responses: Sequence[BaseModel | dict[str, object]],
        *,
        usage: TokenUsage | None = None,
        model: str = "fake-model",
    ) -> None:
        self._responses = list(responses)
        self._usage = usage or TokenUsage(input_tokens=0, output_tokens=0)
        self._model = model
        self.calls = 0

    @property
    def mode(self) -> LLMMode:
        return LLMMode.OFF

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_model: type[T],
        max_output_tokens: int,
        purpose: str,
        run_id: str,
    ) -> Completion[T]:
        del messages, max_output_tokens, purpose, run_id
        if not self._responses:
            raise LLMRequestError("Fake client has no response configured.")
        raw = self._responses.pop(0)
        self.calls += 1
        try:
            value = _validate_response(response_model, raw)
        except (ValidationError, TypeError, ValueError):
            raise LLMOutputError(
                "Model output did not match the required response schema."
            ) from None
        return Completion(value=value, usage=self._usage, model=self._model)


class LiveClient:
    """The only client allowed to make network requests, guarded by cost and concurrency locks."""

    def __init__(
        self,
        settings: Settings,
        *,
        ledger: BudgetLedger,
        sdk_client: OpenAI | None = None,
    ) -> None:
        if settings.llm_mode is not LLMMode.LIVE or not settings.allow_live_llm:
            raise LLMRequestError("Live client requires explicit live-mode configuration.")
        if not settings.has_api_key or settings.model_api_key is None:
            raise LLMRequestError("Live client requires MODEL_API_KEY.")
        self.settings = settings
        self.ledger = ledger
        self._request_lock = FileLock(settings.data_dir / "llm" / "live-request.lock")
        self._client = sdk_client or OpenAI(
            api_key=settings.model_api_key.get_secret_value(),
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    @property
    def mode(self) -> LLMMode:
        return self.settings.llm_mode

    def _output_limit(self, purpose: str) -> int:
        """Planning and explanation have separate completion allowances (ADR-027, ADR-028)."""
        if purpose == "plan":
            return self.settings.llm_max_planning_output_tokens
        if purpose == "explanation":
            return self.settings.llm_max_explanation_output_tokens
        return self.settings.llm_max_output_tokens_per_call

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_model: type[T],
        max_output_tokens: int,
        purpose: str,
        run_id: str,
    ) -> Completion[T]:
        estimated_input = estimate_input_tokens(messages)
        if estimated_input > self.settings.llm_max_input_tokens_per_call:
            raise TokenLimitError(
                f"Estimated input exceeds the "
                f"{self.settings.llm_max_input_tokens_per_call}-token per-call target."
            )
        output_limit = self._output_limit(purpose)
        if max_output_tokens > output_limit:
            raise TokenLimitError(f"Output exceeds the {output_limit}-token per-call cap.")
        sdk_messages = [_sdk_message(message) for message in messages]
        response_format = _json_schema_format(response_model)
        try:
            (self.settings.data_dir / "llm").mkdir(parents=True, exist_ok=True)
        except OSError:
            raise BudgetStateError(
                "Live request lock directory is unavailable; live requests are disabled."
            ) from None
        if not self._request_lock.acquire():
            raise BudgetStateError(
                "Another live request is active; parallel requests are disabled."
            )

        reservation: BudgetReservation | None = None
        request_id = str(uuid.uuid4())
        provider_request_attempted = False
        metadata: _ResponseMetadata | None = None
        try:
            reservation = self.ledger.reserve(
                request_id=request_id,
                run_id=run_id,
                estimated_input_tokens=estimated_input,
                max_output_tokens=max_output_tokens,
            )
            try:
                provider_request_attempted = True
                if purpose in _LOW_REASONING_PURPOSES:
                    response = self._client.chat.completions.create(
                        model=self.settings.llm_model,
                        messages=sdk_messages,
                        max_completion_tokens=max_output_tokens,
                        response_format=response_format,
                        reasoning_effort="low",
                    )
                else:
                    response = self._client.chat.completions.create(
                        model=self.settings.llm_model,
                        messages=sdk_messages,
                        max_completion_tokens=max_output_tokens,
                        response_format=response_format,
                    )
            except APIError as exc:
                self.ledger.settle(
                    reservation,
                    usage=None,
                    model=self.settings.llm_model,
                    outcome=f"provider_error:{type(exc).__name__}",
                )
                raise LLMRequestError(
                    f"Meta Model API request failed ({type(exc).__name__}); no provider detail "
                    "was exposed.",
                    model=self.settings.llm_model,
                ) from None

            metadata = _response_metadata(response, fallback_model=self.settings.llm_model)
            usage = _usage_from_response(response)
            if metadata.refused:
                self.ledger.settle(
                    reservation,
                    usage=usage,
                    model=metadata.model,
                    outcome="refused",
                    response_id=metadata.response_id,
                    finish_reason=metadata.finish_reason,
                    visible_content=metadata.visible_content,
                )
                raise LLMRefusalError(
                    "The provider refused the request; refusal content was not retained."
                )
            if metadata.finish_reason == "content_filter":
                self.ledger.settle(
                    reservation,
                    usage=usage,
                    model=metadata.model,
                    outcome="content_filter",
                    response_id=metadata.response_id,
                    finish_reason=metadata.finish_reason,
                    visible_content=metadata.visible_content,
                )
                raise LLMContentFilterError(
                    "The provider filtered the response; filtered content was not retained."
                )
            if metadata.finish_reason == "length":
                self.ledger.settle(
                    reservation,
                    usage=usage,
                    model=metadata.model,
                    outcome="token_limit",
                    response_id=metadata.response_id,
                    finish_reason=metadata.finish_reason,
                    visible_content=metadata.visible_content,
                )
                raise TokenLimitError(
                    "Provider output was truncated by the completion-token limit."
                )
            if usage is None:
                self.ledger.settle(
                    reservation,
                    usage=None,
                    model=metadata.model,
                    outcome="usage_unavailable",
                    response_id=metadata.response_id,
                    finish_reason=metadata.finish_reason,
                    visible_content=metadata.visible_content,
                )
                raise BudgetStateError(
                    "Provider usage was unavailable; maximum reserved cost was charged."
                )
            if usage.input_tokens > self.settings.llm_max_input_tokens_per_call:
                self.ledger.settle(
                    reservation,
                    usage=usage,
                    model=metadata.model,
                    outcome="usage_limit_exceeded",
                    response_id=metadata.response_id,
                    finish_reason=metadata.finish_reason,
                    visible_content=metadata.visible_content,
                )
                raise TokenLimitError("Provider usage exceeded the configured input token limit.")
            if usage.output_tokens > max_output_tokens:
                self.ledger.settle(
                    reservation,
                    usage=usage,
                    model=metadata.model,
                    outcome="token_limit",
                    response_id=metadata.response_id,
                    finish_reason=metadata.finish_reason,
                    visible_content=metadata.visible_content,
                )
                raise TokenLimitError(
                    "Provider usage exceeded the configured completion-token limit."
                )
            content = _content_from_response(response)
            if content is None:
                outcome = (
                    "token_limit" if usage.output_tokens >= max_output_tokens else "missing_output"
                )
                self.ledger.settle(
                    reservation,
                    usage=usage,
                    model=metadata.model,
                    outcome=outcome,
                    response_id=metadata.response_id,
                    finish_reason=metadata.finish_reason,
                    visible_content=metadata.visible_content,
                )
                if outcome == "token_limit":
                    raise TokenLimitError(
                        "Provider output ended at the completion-token limit without content."
                    )
                raise LLMMissingOutputError("Provider returned no visible completion content.")
            try:
                value = _validate_response_json(response_model, content)
            except (ValidationError, TypeError, ValueError):
                if usage.output_tokens >= max_output_tokens:
                    self.ledger.settle(
                        reservation,
                        usage=usage,
                        model=metadata.model,
                        outcome="token_limit",
                        response_id=metadata.response_id,
                        finish_reason=metadata.finish_reason,
                        visible_content=metadata.visible_content,
                    )
                    raise TokenLimitError(
                        "Provider output reached the completion-token limit before validation."
                    ) from None
                self.ledger.settle(
                    reservation,
                    usage=usage,
                    model=metadata.model,
                    outcome="invalid_output",
                    response_id=metadata.response_id,
                    finish_reason=metadata.finish_reason,
                    visible_content=metadata.visible_content,
                )
                raise LLMOutputError(
                    "Model output did not match the required response schema."
                ) from None
            self.ledger.settle(
                reservation,
                usage=usage,
                model=metadata.model,
                outcome="success",
                response_id=metadata.response_id,
                finish_reason=metadata.finish_reason,
                visible_content=metadata.visible_content,
            )
            return Completion(
                value=value,
                usage=usage,
                model=metadata.model,
                response_id=metadata.response_id,
                provider_request_attempted=True,
            )
        except LLMClientError as exc:
            if provider_request_attempted:
                exc.provider_request_attempted = True
            if metadata is not None and exc.model is None:
                exc.model = metadata.model
            raise
        finally:
            self._request_lock.release()


class RecordingClient:
    """Persist response fixtures and request hashes, never raw prompts or credentials."""

    def __init__(self, client: LLMClient, directory: Path) -> None:
        self.client = client
        self.directory = directory

    @property
    def mode(self) -> LLMMode:
        return self.client.mode

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_model: type[T],
        max_output_tokens: int,
        purpose: str,
        run_id: str,
    ) -> Completion[T]:
        completion = self.client.complete(
            messages,
            response_model=response_model,
            max_output_tokens=max_output_tokens,
            purpose=purpose,
            run_id=run_id,
        )
        prompt_hash = _request_hash(messages, response_model, max_output_tokens, purpose)
        content = _scrub_key_shaped_values(completion.value.model_dump(mode="json"))
        payload = {
            "version": 1,
            "request_hash": prompt_hash,
            "purpose": purpose,
            "response_model": response_model.__name__,
            "model": completion.model,
            "response_id": completion.response_id,
            "usage": {
                "input_tokens": completion.usage.input_tokens,
                "output_tokens": completion.usage.output_tokens,
                "cached_input_tokens": completion.usage.cached_input_tokens,
            },
            "content": content,
        }
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / f"{uuid.uuid4().hex}.json"
            temporary = path.with_suffix(".tmp")
            temporary.write_text(canonical_json(payload), encoding="utf-8")
            temporary.replace(path)
        except OSError:
            logger.error("LLM response recording failed; response content was not logged.")
            raise LLMRequestError("LLM response recording failed.") from None
        return completion


class ReplayClient:
    """Replay matching sanitized recordings entirely offline."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._recordings = sorted(directory.glob("*.json"))
        self._position = 0

    @property
    def mode(self) -> LLMMode:
        return LLMMode.REPLAY

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        response_model: type[T],
        max_output_tokens: int,
        purpose: str,
        run_id: str,
    ) -> Completion[T]:
        del run_id
        if self._position >= len(self._recordings):
            raise ReplayMismatchError("No matching offline recording is available.")
        path = self._recordings[self._position]
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ReplayMismatchError("Offline recording is unreadable.") from None
        expected_hash = _request_hash(messages, response_model, max_output_tokens, purpose)
        if (
            payload.get("version") != 1
            or payload.get("request_hash") != expected_hash
            or payload.get("purpose") != purpose
            or payload.get("response_model") != response_model.__name__
        ):
            raise ReplayMismatchError("Offline recording does not match this request.")
        try:
            value = _validate_response(response_model, payload["content"])
            usage = TokenUsage(**payload["usage"])
            model = str(payload["model"])
        except (KeyError, TypeError, ValueError, ValidationError):
            raise ReplayMismatchError("Offline recording does not validate.") from None
        self._position += 1
        return Completion(
            value=value,
            usage=usage,
            model=model,
            response_id=payload.get("response_id"),
        )


def estimate_input_tokens(messages: Sequence[ChatMessage]) -> int:
    """Conservative byte-based estimate plus message overhead; no tokenizer dependency."""
    return sum(
        len(message.content.encode("utf-8")) + len(message.role) + 32 for message in messages
    )


def _usage_from_response(response: object) -> TokenUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    details = getattr(usage, "prompt_tokens_details", None)
    completion_details = getattr(usage, "completion_tokens_details", None)
    try:
        reasoning_tokens_value = getattr(completion_details, "reasoning_tokens", None)
        return TokenUsage(
            input_tokens=int(usage.prompt_tokens),
            output_tokens=int(usage.completion_tokens),
            cached_input_tokens=int(getattr(details, "cached_tokens", 0) or 0),
            reasoning_tokens=(
                int(reasoning_tokens_value) if reasoning_tokens_value is not None else None
            ),
        )
    except (AttributeError, TypeError, ValueError):
        return None


def _response_metadata(response: ChatCompletion, *, fallback_model: str) -> _ResponseMetadata:
    response_model = getattr(response, "model", None)
    model = (
        response_model.strip()
        if isinstance(response_model, str) and _SAFE_METADATA_ID.fullmatch(response_model.strip())
        else fallback_model
    )
    response_id_value = getattr(response, "id", None)
    response_id = (
        response_id_value.strip()
        if isinstance(response_id_value, str)
        and _SAFE_METADATA_ID.fullmatch(response_id_value.strip())
        else None
    )
    try:
        choice = response.choices[0]
        message = choice.message
    except (AttributeError, IndexError, TypeError):
        choice = None
        message = None
    finish_reason_value = getattr(choice, "finish_reason", None)
    finish_reason = (
        finish_reason_value
        if isinstance(finish_reason_value, str)
        and _SAFE_FINISH_REASON.fullmatch(finish_reason_value)
        else None
    )
    content = getattr(message, "content", None)
    visible_content = isinstance(content, str) and bool(content.strip())
    refusal = getattr(message, "refusal", None)
    return _ResponseMetadata(
        model=model,
        response_id=response_id,
        finish_reason=finish_reason,
        visible_content=visible_content if message is not None else None,
        refused=isinstance(refusal, str) and bool(refusal.strip()),
    )


def _content_from_response(response: ChatCompletion) -> str | None:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError):
        return None
    return content if isinstance(content, str) and content.strip() else None


def _validate_response_json(response_model: type[T], content: str) -> T:
    return _validate_response(response_model, json.loads(content))


def _validate_response(response_model: type[T], payload: object) -> T:
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    if response_model is ReviewPlan and (not isinstance(payload, dict) or "checks" not in payload):
        raise ValueError("A review plan must include the checks field.")
    return response_model.model_validate(payload)


def _json_schema_format(response_model: type[BaseModel]) -> ResponseFormatJSONSchema:
    schema = response_model.model_json_schema()
    if response_model is ReviewPlan:
        properties = schema.get("properties")
        if isinstance(properties, dict):
            schema["required"] = list(properties)
    schema_name = re.sub(r"[^a-zA-Z0-9_-]", "_", response_model.__name__).strip("_").lower()[:64]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name or "response",
            "schema": schema,
        },
    }


def _sdk_message(
    message: ChatMessage,
) -> ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam:
    if message.role == "system":
        return {"role": "system", "content": message.content}
    return {"role": "user", "content": message.content}


def _request_hash(
    messages: Sequence[ChatMessage],
    response_model: type[BaseModel],
    max_output_tokens: int,
    purpose: str,
) -> str:
    payload = {
        "messages": [message.model_dump(mode="json") for message in messages],
        "response_model": response_model.__name__,
        "max_output_tokens": max_output_tokens,
        "purpose": purpose,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _scrub_key_shaped_values(value: object) -> object:
    if isinstance(value, str):
        return _MODEL_KEY_PATTERN.sub("[redacted]", value)
    if isinstance(value, list):
        return [_scrub_key_shaped_values(item) for item in value]
    if isinstance(value, dict):
        return {key: _scrub_key_shaped_values(item) for key, item in value.items()}
    return value
