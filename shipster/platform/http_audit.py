"""Global HTTP audit: logs request metadata and optional redacted body previews."""

from __future__ import annotations

import json
import logging
from time import perf_counter
from urllib.parse import parse_qs

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from shipster.platform.settings import get_global_settings

HTTP_AUDIT_LOGGER = "shipster.audit.http"

_MAX_REQUEST_BODY_BYTES = 8_192
_MAX_RESPONSE_BODY_BYTES = 8_192
_REDACTED_KEYS = frozenset({"access_token", "authorization", "password", "refresh_token", "token"})

_LOG = logging.getLogger(HTTP_AUDIT_LOGGER)


def _decode_preview(data: bytes, limit: int) -> str:
    clipped = data[:limit]
    return clipped.decode("utf-8", errors="replace")


def _redact_json(value: object) -> object:
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, item in value.items():
            if str(key).lower() in _REDACTED_KEYS:
                redacted[str(key)] = "***REDACTED***"
            else:
                redacted[str(key)] = _redact_json(item)
        return redacted
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    return value


def _sanitize_preview(text: str) -> str:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(_redact_json(parsed), separators=(",", ":"))


async def _buffer_http_request_messages(
    receive: Receive, *, capture_limit: int
) -> tuple[list[Message], bytes]:
    """Read all ASGI ``http.request`` messages until the body is complete or disconnect."""
    messages: list[Message] = []
    body_parts: list[bytes] = []
    total = 0
    while True:
        msg = await receive()
        messages.append(msg)
        if msg["type"] == "http.disconnect":
            break
        if msg["type"] == "http.request":
            chunk = msg.get("body") or b""
            if total < capture_limit:
                take = chunk[: max(0, capture_limit - total)]
                body_parts.append(take)
                total += len(take)
            if not msg.get("more_body", False):
                break
    return messages, b"".join(body_parts)


def _response_status_and_body(
    sent: list[Message], *, capture_limit: int
) -> tuple[int | None, bytes]:
    status: int | None = None
    out = bytearray()
    for msg in sent:
        if msg["type"] == "http.response.start":
            status = msg["status"]
        elif msg["type"] == "http.response.body":
            chunk = msg.get("body") or b""
            need = capture_limit - len(out)
            if need > 0:
                out.extend(chunk[:need])
    return status, bytes(out)


class HttpAuditMiddleware:
    """
    ASGI middleware that records each HTTP exchange: method/path/query, path params (after routing),
    optional request/response body previews, status, and elapsed seconds.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._log_bodies = get_global_settings().http_audit_log_bodies

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = perf_counter()
        req_capture_limit = _MAX_REQUEST_BODY_BYTES if self._log_bodies else 0
        resp_capture_limit = _MAX_RESPONSE_BODY_BYTES if self._log_bodies else 0
        req_messages, req_body_preview = await _buffer_http_request_messages(
            receive,
            capture_limit=req_capture_limit,
        )

        sent_messages: list[Message] = []

        async def send_wrapper(message: Message) -> None:
            sent_messages.append(message)
            await send(message)

        idx = 0

        async def receive_replay() -> Message:
            nonlocal idx
            if idx < len(req_messages):
                m = req_messages[idx]
                idx += 1
                return m
            return await receive()

        try:
            await self.app(scope, receive_replay, send_wrapper)
        finally:
            duration_s = perf_counter() - started
            status_code, resp_body = _response_status_and_body(
                sent_messages,
                capture_limit=resp_capture_limit,
            )
            query_raw = scope.get("query_string") or b""
            query_params = _redact_json(
                parse_qs(query_raw.decode("latin-1"), keep_blank_values=True),
            )
            path_params = _redact_json(dict(scope.get("path_params") or {}))
            extra = {
                "event": "http_audit",
                "http_method": scope.get("method"),
                "path": scope.get("path"),
                "query": query_params,
                "path_params": path_params,
                "status_code": status_code,
                "duration_s": round(duration_s, 4),
            }
            if self._log_bodies:
                extra["request_body"] = _sanitize_preview(
                    _decode_preview(req_body_preview, _MAX_REQUEST_BODY_BYTES),
                )
                extra["response_body"] = _sanitize_preview(
                    _decode_preview(resp_body, _MAX_RESPONSE_BODY_BYTES),
                )
            _LOG.info("HTTP audit event", extra=extra)
