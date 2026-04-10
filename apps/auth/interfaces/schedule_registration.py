"""Periodic jobs for auth (token cleanup, outbox, etc.)."""

from shipster.platform.scheduler.registry import ScheduleRegistry


def register(_registry: ScheduleRegistry) -> None:
    """Register APScheduler interval jobs."""
