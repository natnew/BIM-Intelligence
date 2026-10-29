"""Sanitised failures at the provider boundary and the local spend-control boundary."""


class LLMClientError(Exception):
    """Base class for failures that can safely be handled without exposing provider details."""


class LLMUnavailableError(LLMClientError):
    """No client is enabled for this operation."""


class LLMRequestError(LLMClientError):
    """The provider request failed; the underlying response is intentionally not exposed."""


class LLMOutputError(LLMClientError):
    """Provider content did not validate against the requested Pydantic response model."""


class ReplayMismatchError(LLMClientError):
    """A local replay record does not match the requested operation."""


class BudgetLimitError(LLMClientError):
    """A request would exceed a configured application-level budget or call limit."""


class BudgetStateError(LLMClientError):
    """Persistent budget state or its lock cannot be trusted."""


class LiveConcurrencyError(LLMClientError):
    """A live request is already in progress; parallel requests are disabled."""


class TokenLimitError(LLMClientError):
    """A request exceeds the configured per-call input or output token cap."""
