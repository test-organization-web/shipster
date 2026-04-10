"""Central job ids: use the same strings for APScheduler and ``get_or_create_singleton``."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OrganizationScheduleJobIds:
    """Stable ids for ``ScheduleRegistry.add_interval_job`` and stream singleton keys."""

    poll_invitation_created_events: str = "organizations.poll_invitation_created_events"


ORGANIZATION_SCHEDULE_JOB_IDS = OrganizationScheduleJobIds()
