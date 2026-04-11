"""Periodic jobs for auth (password reset delivery, etc.)."""

import logging

from apps.auth.interfaces.dependencies import build_process_password_reset_notifications
from apps.shared.domain.runtime_catalog import INTERVAL_JOB_IDS
from shipster.platform.persistence import ShipsterUnitOfWork, get_async_session_factory
from shipster.platform.scheduler.registry import ScheduleRegistry
from shipster.platform.settings import get_global_settings

_PASSWORD_RESET_NOTIFICATION_BATCH_SIZE = 20

_LOG = logging.getLogger(__name__)


async def run_password_reset_notification_poll() -> None:
    _LOG.debug("auth scheduler: password reset notification poll started")
    settings = get_global_settings()
    session = get_async_session_factory()()
    try:
        processor = build_process_password_reset_notifications(
            uow=ShipsterUnitOfWork(session),
            settings=settings,
        )
        await processor.execute(limit=_PASSWORD_RESET_NOTIFICATION_BATCH_SIZE)
        await session.commit()
        _LOG.debug("auth scheduler: password reset notification poll committed")
    except Exception:
        _LOG.exception("auth scheduler: password reset notification poll failed")
        await session.rollback()
        raise
    finally:
        await session.close()


def register(registry: ScheduleRegistry) -> None:
    registry.add_interval_job(
        INTERVAL_JOB_IDS.auth.process_pending_password_reset_notifications,
        seconds=get_global_settings().auth_password_reset_requested_poll_seconds,
        func=run_password_reset_notification_poll,
    )
