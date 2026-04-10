"""Collect interval job specs; each bounded context registers from its ``interfaces`` module."""

from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import TypeAlias

# Sync or async job body; APScheduler :class:`~apscheduler.schedulers.asyncio.AsyncIOScheduler`
# runs coroutines on the loop and plain callables in the default executor.
IntervalJobCallable: TypeAlias = Callable[[], None] | Callable[[], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class IntervalJobSpec:
    """Periodic job: ``func`` may be ``def`` or ``async def``."""

    id: str
    seconds: float
    func: IntervalJobCallable


class ScheduleRegistry:
    """Collects jobs at startup for :class:`shipster.platform.scheduler.runner.SchedulerRunner`."""

    def __init__(self) -> None:
        self._jobs: list[IntervalJobSpec] = []

    def add_interval_job(
        self,
        job_id: str,
        *,
        seconds: float,
        func: IntervalJobCallable,
    ) -> None:
        """Register a repeating job (e.g. outbox / stream polling)."""
        if not job_id.strip():
            raise ValueError("job_id must be non-empty")
        if seconds <= 0:
            raise ValueError("seconds must be positive")
        if not callable(func):
            msg = "func must be callable"
            raise TypeError(msg)
        self._jobs.append(IntervalJobSpec(id=job_id, seconds=seconds, func=func))

    def iter_jobs(self) -> Iterator[IntervalJobSpec]:
        return iter(self._jobs)
