"""Periodic jobs for privacy export and erasure processing."""

import logging

from apps.privacy.interfaces.dependencies import (
    build_process_pending_erasure_requests,
    build_process_pending_exports,
)
from apps.shared.domain.runtime_catalog import INTERVAL_JOB_IDS
from shipster.platform.persistence import ShipsterUnitOfWork, get_async_session_factory
from shipster.platform.scheduler.registry import ScheduleRegistry
from shipster.platform.settings import get_global_settings

_PENDING_EXPORT_BATCH_SIZE = 10
_PENDING_ERASURE_BATCH_SIZE = 10

_LOG = logging.getLogger(__name__)


async def run_privacy_pending_export_poll() -> None:
    _LOG.debug("privacy scheduler: pending export poll started")
    settings = get_global_settings()
    session = get_async_session_factory()()
    try:
        processor = build_process_pending_exports(
            session=session,
            uow=ShipsterUnitOfWork(session),
            settings=settings,
        )
        await processor.execute(limit=_PENDING_EXPORT_BATCH_SIZE)
        await session.commit()
        _LOG.debug("privacy scheduler: pending export poll committed")
    except Exception:
        _LOG.exception("privacy scheduler: pending export poll failed")
        await session.rollback()
        raise
    finally:
        await session.close()


async def run_privacy_pending_erasure_poll() -> None:
    _LOG.debug("privacy scheduler: pending erasure poll started")
    settings = get_global_settings()
    session = get_async_session_factory()()
    try:
        processor = build_process_pending_erasure_requests(
            session=session,
            uow=ShipsterUnitOfWork(session),
            settings=settings,
        )
        await processor.execute(limit=_PENDING_ERASURE_BATCH_SIZE)
        await session.commit()
        _LOG.debug("privacy scheduler: pending erasure poll committed")
    except Exception:
        _LOG.exception("privacy scheduler: pending erasure poll failed")
        await session.rollback()
        raise
    finally:
        await session.close()


def register(registry: ScheduleRegistry) -> None:
    registry.add_interval_job(
        INTERVAL_JOB_IDS.privacy.process_pending_exports,
        seconds=get_global_settings().privacy_pending_export_poll_seconds,
        func=run_privacy_pending_export_poll,
    )
    registry.add_interval_job(
        INTERVAL_JOB_IDS.privacy.process_pending_erasure_requests,
        seconds=get_global_settings().privacy_pending_erasure_poll_seconds,
        func=run_privacy_pending_erasure_poll,
    )
