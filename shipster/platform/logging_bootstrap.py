"""Application and server logging bootstrap."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from shipster.platform.http_audit import HTTP_AUDIT_LOGGER
from shipster.platform.settings import GlobalSettings, get_global_settings

REQUEST_TIMING_LOGGER = "shipster.debug.request_timing"

_configured = False

_STANDARD_RECORD_ATTRS = frozenset(logging.makeLogRecord({}).__dict__) | {
    "asctime",
    "color_message",
    "message",
}
_SENSITIVE_LOG_KEYS = frozenset(
    {"access_token", "authorization", "client_addr", "email", "password", "refresh_token", "token"},
)


def _coerce_json_for_key(key: str, value: object) -> object:
    if key.lower() in _SENSITIVE_LOG_KEYS:
        return "***REDACTED***"
    return _coerce_json(value)


def _coerce_json(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC).isoformat()
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _coerce_json_for_key(str(k), v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_coerce_json(v) for v in value]
    return str(value)


class JsonLogFormatter(logging.Formatter):
    """Serialize log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        event = record.__dict__.get("event")
        if event is not None:
            payload["event"] = _coerce_json(event)

        if record.name == "uvicorn.access" and len(record.args) == 5:
            client_addr, method, path, http_version, status_code = record.args
            payload.update(
                {
                    "client_addr": _coerce_json_for_key("client_addr", client_addr),
                    "http_method": _coerce_json_for_key("http_method", method),
                    "path": _coerce_json_for_key("path", path),
                    "http_version": _coerce_json_for_key("http_version", http_version),
                    "status_code": _coerce_json_for_key("status_code", status_code),
                },
            )

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_ATTRS or key.startswith("_"):
                continue
            payload[key] = _coerce_json_for_key(key, value)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _resolve_log_level(raw_level: str) -> int:
    level_name = raw_level.upper()
    level = logging.getLevelName(level_name)
    if isinstance(level, int):
        return level
    return logging.INFO


def _make_handler(*, stream: object, settings: GlobalSettings) -> logging.Handler:
    handler = logging.StreamHandler(stream)
    handler.setLevel(_resolve_log_level(settings.log_level))
    if settings.json_logs:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    return handler


def _configure_named_logger(
    name: str,
    *,
    level: int,
    handlers: list[logging.Handler] | None,
    propagate: bool,
) -> None:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(level)
    logger.propagate = propagate
    if handlers:
        for handler in handlers:
            logger.addHandler(handler)


def _configure_optional_loggers(settings: GlobalSettings) -> None:
    timing_logger = logging.getLogger(REQUEST_TIMING_LOGGER)
    timing_logger.setLevel(logging.DEBUG if settings.debug_request_timing else logging.INFO)
    timing_logger.propagate = True

    audit_logger = logging.getLogger(HTTP_AUDIT_LOGGER)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = True


def configure_application_logging() -> None:
    """Configure root, Shipster, and Uvicorn logging once per process."""
    global _configured
    if _configured:
        return

    settings = get_global_settings()
    level = _resolve_log_level(settings.log_level)
    stderr_handler = _make_handler(stream=sys.stderr, settings=settings)
    stdout_handler = _make_handler(stream=sys.stdout, settings=settings)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(stderr_handler)

    _configure_named_logger("uvicorn", level=level, handlers=None, propagate=True)
    _configure_named_logger("uvicorn.error", level=level, handlers=None, propagate=True)
    _configure_named_logger("uvicorn.asgi", level=level, handlers=None, propagate=True)
    _configure_named_logger(
        "uvicorn.access",
        level=level,
        handlers=[stdout_handler] if settings.access_log else None,
        propagate=False,
    )

    _configure_optional_loggers(settings)
    _configured = True


async def configure_request_timing_logging() -> None:
    """Preserve compatibility for request-timing bootstrap hooks."""
    configure_application_logging()


async def configure_http_audit_logging() -> None:
    """Preserve compatibility for HTTP-audit bootstrap hooks."""
    configure_application_logging()
