import logging
from dataclasses import dataclass
from uuid import UUID

from apps.privacy.application.get_data_export_status import GetDataExportStatus
from apps.privacy.domain.entities import PrivacyExportLifecycleEvent
from apps.privacy.domain.ports.export_request_repository import ExportRequestRepository

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ListExportLifecycleEventsResult:
    events: list[PrivacyExportLifecycleEvent]
    total: int


class ListExportLifecycleEvents:
    def __init__(
        self,
        *,
        get_export_status: GetDataExportStatus,
        requests: ExportRequestRepository,
    ) -> None:
        self._get_export_status = get_export_status
        self._requests = requests

    async def execute(
        self,
        *,
        request_id: UUID,
        subject_user_id: UUID,
        limit: int,
        offset: int,
    ) -> ListExportLifecycleEventsResult:
        await self._get_export_status.execute(
            request_id=request_id,
            subject_user_id=subject_user_id,
        )
        limit_clamped = max(1, min(500, limit))
        offset_clamped = max(0, offset)
        events = await self._requests.list_lifecycle_events(
            export_request_id=request_id,
            limit=limit_clamped,
            offset=offset_clamped,
        )
        total = await self._requests.count_lifecycle_events(export_request_id=request_id)
        _LOG.debug(
            "privacy export: listed lifecycle events",
            extra={
                "export_request_id": str(request_id),
                "returned": len(events),
                "total": total,
            },
        )
        return ListExportLifecycleEventsResult(events=events, total=total)
