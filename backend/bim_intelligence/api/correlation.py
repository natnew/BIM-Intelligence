"""Request correlation ids (ARCHITECTURE §15).

Every response carries ``X-Correlation-ID``; a well-formed client-supplied value is echoed so
that a browser session can be matched against server logs, otherwise a fresh id is minted.
Pure ASGI so it composes with streaming responses and background tasks.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from starlette.datastructures import Headers, MutableHeaders

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

CORRELATION_HEADER = "X-Correlation-ID"
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def correlation_id_from_scope(scope: Scope) -> str | None:
    state = scope.get("state")
    return state.get("correlation_id") if isinstance(state, dict) else None


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        supplied = Headers(scope=scope).get(CORRELATION_HEADER.lower())
        correlation_id = supplied if supplied and _SAFE_ID.match(supplied) else new_correlation_id()
        scope.setdefault("state", {})["correlation_id"] = correlation_id

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers[CORRELATION_HEADER] = correlation_id
            await send(message)

        await self.app(scope, receive, send_with_header)
