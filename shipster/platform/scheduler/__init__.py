"""Periodic tasks: registry, APScheduler runner, UoW-scoped job helper."""

from apps.shared.domain.ports.stream_consumer_params import StreamConsumerParams
from shipster.platform.scheduler.bootstrap import build_schedule_registry, create_scheduler_runner
from shipster.platform.scheduler.registry import IntervalJobSpec, ScheduleRegistry
from shipster.platform.scheduler.runner import SchedulerRunner
from shipster.platform.scheduler.safe_poll import run_poll_with_logging
from shipster.platform.scheduler.singleton_cache import get_or_create_singleton
from shipster.platform.scheduler.uow_scope import uow_interval_job

__all__ = [
    "IntervalJobSpec",
    "ScheduleRegistry",
    "SchedulerRunner",
    "StreamConsumerParams",
    "build_schedule_registry",
    "create_scheduler_runner",
    "get_or_create_singleton",
    "run_poll_with_logging",
    "uow_interval_job",
]
