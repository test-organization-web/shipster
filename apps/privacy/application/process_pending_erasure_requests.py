import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from apps.privacy.domain.entities import PrivacyErasureRequest, PrivacyErasureStatus
from apps.privacy.domain.ports.erasure_request_repository import ErasureRequestRepository
from apps.privacy.domain.ports.subject_data_eraser import SubjectDataEraser

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProcessPendingErasureRequests:
    erasures: ErasureRequestRepository
    privacy_eraser: SubjectDataEraser
    organizations_eraser: SubjectDataEraser
    users_eraser: SubjectDataEraser
    orders_eraser: SubjectDataEraser

    async def execute(self, *, limit: int = 10) -> None:
        pending = await self.erasures.list_pending(limit=limit)
        if pending:
            _LOG.debug(
                "privacy erasure worker: batch",
                extra={"pending_count": len(pending)},
            )
        for request in pending:
            await self._process_one(request)

    async def _process_one(self, request: PrivacyErasureRequest) -> None:
        _LOG.info(
            "privacy erasure worker: processing request",
            extra={
                "erasure_request_id": str(request.id),
                "subject_user_id": str(request.subject_user_id),
            },
        )
        started_at = datetime.now(UTC)
        await self.erasures.save(
            replace(
                request,
                status=PrivacyErasureStatus.PROCESSING,
                updated_at=started_at,
                failure_reason=None,
            ),
        )
        subject_user_id = request.subject_user_id
        try:
            await self.privacy_eraser.erase_for_user(subject_user_id)
            await self.organizations_eraser.erase_for_user(subject_user_id)
            await self.users_eraser.erase_for_user(subject_user_id)
            await self.orders_eraser.erase_for_user(subject_user_id)
        except Exception as exc:
            _LOG.exception(
                "privacy erasure worker: erasure failed",
                extra={
                    "erasure_request_id": str(request.id),
                    "subject_user_id": str(subject_user_id),
                },
            )
            await self.erasures.save(
                replace(
                    request,
                    status=PrivacyErasureStatus.FAILED,
                    updated_at=datetime.now(UTC),
                    failure_reason=str(exc)[:1024],
                ),
            )
            return

        await self.erasures.save(
            replace(
                request,
                status=PrivacyErasureStatus.COMPLETED,
                updated_at=datetime.now(UTC),
                failure_reason=None,
            ),
        )
        _LOG.info(
            "privacy erasure worker: erasure completed",
            extra={
                "erasure_request_id": str(request.id),
                "subject_user_id": str(subject_user_id),
            },
        )
