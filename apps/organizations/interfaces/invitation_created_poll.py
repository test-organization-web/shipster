"""Wires the invitation-created poll job to platform messaging and settings."""

from apps.organizations.application.messaging import create_invitation_created_processor
from apps.organizations.interfaces.schedule_job_ids import ORGANIZATION_SCHEDULE_JOB_IDS
from apps.shared.domain.ports.stream_consumer_params import StreamConsumerParams
from shipster.platform.messaging.deps import (
    ensure_message_receiver,
    ensure_organization_invitation_created_handler,
)
from shipster.platform.scheduler.safe_poll import run_poll_with_logging
from shipster.platform.scheduler.singleton_cache import get_or_create_singleton
from shipster.platform.settings import get_global_settings

JOB_IDS = ORGANIZATION_SCHEDULE_JOB_IDS


async def run_organization_invitation_created_poll() -> None:
    """APScheduler entrypoint: enabled flag and deps live in the composition root."""
    settings = get_global_settings()
    if not settings.org_invitation_consumer_enabled:
        return

    params = StreamConsumerParams(
        subscription=settings.org_invitation_subscription,
        consumer_id=settings.consumer_id,
    )

    processor = get_or_create_singleton(
        JOB_IDS.poll_invitation_created_events,
        lambda: create_invitation_created_processor(
            ensure_message_receiver(),
            ensure_organization_invitation_created_handler(),
            params,
        ),
    )
    await run_poll_with_logging(
        processor.execute,
        event_name="organization invitation created poll",
    )
