from typing import Protocol
from uuid import UUID

from apps.privacy.domain.entities import PrivacyExportLifecycleEvent, PrivacyExportRequest


class ExportRequestRepository(Protocol):
    async def get_by_id(self, request_id: UUID) -> PrivacyExportRequest | None:
        """Return export request by id."""

    async def save(self, request: PrivacyExportRequest) -> None:
        """Persist new or updated export request."""

    async def list_pending(self, *, limit: int) -> list[PrivacyExportRequest]:
        """Return pending export requests, oldest first."""

    async def list_ready(self, *, limit: int) -> list[PrivacyExportRequest]:
        """Return ready export requests for retention/integrity maintenance."""

    async def list_lifecycle_events(
        self,
        *,
        export_request_id: UUID,
        limit: int,
        offset: int,
    ) -> list[PrivacyExportLifecycleEvent]:
        """Return lifecycle events for one export request, oldest first."""

    async def count_lifecycle_events(self, *, export_request_id: UUID) -> int:
        """Return total lifecycle event count for one export request."""

    async def list_all_for_subject_user(self, subject_user_id: UUID) -> list[PrivacyExportRequest]:
        """Return all export requests for a subject (any status), oldest first."""
