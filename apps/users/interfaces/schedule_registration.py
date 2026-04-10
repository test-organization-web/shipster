"""Periodic jobs for users (public events, outbox, etc.)."""

from shipster.platform.scheduler.registry import ScheduleRegistry


def register(_registry: ScheduleRegistry) -> None:
    """Register APScheduler interval jobs."""
