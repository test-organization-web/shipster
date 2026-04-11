"""Stable APScheduler interval job identifiers for the privacy bounded context."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PrivacyIntervalJobIds:
    process_pending_exports: str
    process_pending_erasure_requests: str


PRIVACY_INTERVAL_JOB_IDS = PrivacyIntervalJobIds(
    process_pending_exports="privacy.process_pending_exports",
    process_pending_erasure_requests="privacy.process_pending_erasure_requests",
)
