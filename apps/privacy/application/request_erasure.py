import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from apps.privacy.domain.entities import PrivacyErasureRequest, PrivacyErasureStatus
from apps.privacy.domain.errors import (
    PrivacyErasureConflictError,
    PrivacyErasureSubjectNotFoundError,
)
from apps.privacy.domain.ports.erasure_request_repository import ErasureRequestRepository
from apps.users.domain.ports.user_repository import UserRepository

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RequestErasure:
    users: UserRepository
    erasures: ErasureRequestRepository

    async def execute(self, *, subject_user_id: UUID) -> PrivacyErasureRequest:
        if await self.users.get_by_id(subject_user_id) is None:
            raise PrivacyErasureSubjectNotFoundError()
        active = await self.erasures.find_active_for_subject(subject_user_id)
        if active is not None:
            raise PrivacyErasureConflictError()
        now = datetime.now(UTC)
        request = PrivacyErasureRequest(
            id=uuid4(),
            subject_user_id=subject_user_id,
            status=PrivacyErasureStatus.PENDING,
            created_at=now,
            updated_at=now,
            failure_reason=None,
        )
        await self.erasures.save(request)
        _LOG.info(
            "privacy erasure: request created",
            extra={
                "erasure_request_id": str(request.id),
                "subject_user_id": str(subject_user_id),
            },
        )
        return request
