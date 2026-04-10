"""Background worker entrypoint for scheduled jobs."""

from __future__ import annotations

import asyncio
import logging
import signal

from shipster.platform.logging_bootstrap import configure_application_logging
from shipster.platform.persistence.database import init_async_database
from shipster.platform.redis_client import close_async_redis
from shipster.platform.scheduler.bootstrap import create_scheduler_runner
from shipster.platform.settings import get_global_settings

_LOG = logging.getLogger(__name__)


def _install_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            # Fallback for runtimes without asyncio signal handler support.
            signal.signal(sig, lambda _signum, _frame: stop_event.set())


async def _run_worker() -> None:
    configure_application_logging()
    settings = get_global_settings()
    if not settings.background_jobs_enabled:
        msg = "Background jobs disabled; worker cannot start"
        _LOG.error(
            msg,
            extra={"event": "worker_background_jobs_disabled"},
        )
        raise RuntimeError(msg)

    stop_event = asyncio.Event()
    _install_signal_handlers(stop_event)

    _LOG.info("Shipster worker startup beginning", extra={"event": "worker_startup_begin"})
    runner = None
    try:
        await init_async_database()
        _LOG.info("Database initialized", extra={"event": "database_initialized"})
        runner = create_scheduler_runner()
        runner.start()
        _LOG.info("Worker scheduler started", extra={"event": "scheduler_started"})
        await stop_event.wait()
    finally:
        _LOG.info("Shipster worker shutdown beginning", extra={"event": "worker_shutdown_begin"})
        if runner is not None:
            runner.shutdown(wait=True)
            _LOG.info("Worker scheduler stopped", extra={"event": "scheduler_stopped"})
        await close_async_redis()
        _LOG.info("Shipster worker shutdown complete", extra={"event": "worker_shutdown_complete"})


def main() -> None:
    asyncio.run(_run_worker())


if __name__ == "__main__":
    main()
