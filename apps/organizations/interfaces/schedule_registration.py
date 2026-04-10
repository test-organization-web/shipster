"""Periodic jobs for organizations (public events, outbox, etc.)."""

from apps.organizations.interfaces.invitation_created_poll import (
    run_organization_invitation_created_poll,
)
from apps.organizations.interfaces.schedule_job_ids import ORGANIZATION_SCHEDULE_JOB_IDS
from shipster.platform.scheduler.registry import ScheduleRegistry
from shipster.platform.settings import get_global_settings

JOB_IDS = ORGANIZATION_SCHEDULE_JOB_IDS


def register(registry: ScheduleRegistry) -> None:
    """Register APScheduler interval jobs."""
    interval = get_global_settings().org_invitation_poll_seconds
    registry.add_interval_job(
        JOB_IDS.poll_invitation_created_events,
        seconds=interval,
        func=run_organization_invitation_created_poll,
    )
