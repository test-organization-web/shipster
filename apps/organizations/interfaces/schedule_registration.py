"""Periodic jobs for organizations."""

from shipster.platform.scheduler.registry import ScheduleRegistry


def register(registry: ScheduleRegistry) -> None:
    """Organizations currently register no periodic jobs."""
    del registry
