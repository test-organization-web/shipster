"""Wrap stream/outbox poll steps so scheduler jobs log failures without crashing the runner."""

import inspect
import logging
from collections.abc import Awaitable, Callable


async def run_poll_with_logging(
    execute: Callable[[], None] | Callable[[], Awaitable[None]],
    *,
    event_name: str,
    logger: logging.Logger | None = None,
) -> None:
    """Await a poll step; log any exception (use from ``async def`` APScheduler jobs)."""
    log = logger or logging.getLogger(__name__)
    try:
        if inspect.iscoroutinefunction(execute):
            await execute()
        else:
            execute()
    except Exception:
        log.exception("%s failed", event_name)
