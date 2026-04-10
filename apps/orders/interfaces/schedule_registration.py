"""Periodic jobs for orders (DB polling, public / integration events)."""

from shipster.platform.scheduler.registry import ScheduleRegistry


def register(_registry: ScheduleRegistry) -> None:
    """Register APScheduler interval jobs."""
