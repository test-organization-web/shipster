"""Compose schedule registrations from all bounded contexts."""

from apps.auth.interfaces import schedule_registration as auth_schedules
from apps.orders.interfaces import schedule_registration as orders_schedules
from apps.organizations.interfaces import schedule_registration as organizations_schedules
from apps.privacy.interfaces import schedule_registration as privacy_schedules
from apps.users.interfaces import schedule_registration as users_schedules
from shipster.platform.scheduler.registry import ScheduleRegistry
from shipster.platform.scheduler.runner import SchedulerRunner


def build_schedule_registry() -> ScheduleRegistry:
    registry = ScheduleRegistry()
    auth_schedules.register(registry)
    users_schedules.register(registry)
    orders_schedules.register(registry)
    organizations_schedules.register(registry)
    privacy_schedules.register(registry)
    return registry


def create_scheduler_runner() -> SchedulerRunner:
    """Return a process-wide runner; call :meth:`~SchedulerRunner.start` during app startup."""
    return SchedulerRunner(build_schedule_registry())
