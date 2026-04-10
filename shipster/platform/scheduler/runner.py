"""APScheduler 3.x asyncio scheduler — runs on the app event loop."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from shipster.platform.scheduler.registry import ScheduleRegistry


class SchedulerRunner:
    """Starts and stops an :class:`~apscheduler.schedulers.asyncio.AsyncIOScheduler`.

    Uses the **current** asyncio event loop (call :meth:`start` from app lifespan / async context).
    Job callables may be ``def`` (run in the loop's default executor) or ``async def`` (native).
    """

    def __init__(self, registry: ScheduleRegistry) -> None:
        self._scheduler = AsyncIOScheduler()
        seen: set[str] = set()
        for spec in registry.iter_jobs():
            if spec.id in seen:
                msg = f"duplicate schedule job id: {spec.id!r}"
                raise ValueError(msg)
            seen.add(spec.id)
            self._scheduler.add_job(
                spec.func,
                IntervalTrigger(seconds=spec.seconds),
                id=spec.id,
                max_instances=1,
                coalesce=True,
                replace_existing=True,
            )

    def start(self) -> None:
        """Start the scheduler (synchronous; requires a running event loop)."""
        self._scheduler.start()

    def shutdown(self, *, wait: bool = True) -> None:
        """Stop the scheduler (synchronous)."""
        self._scheduler.shutdown(wait=wait)
