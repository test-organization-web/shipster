from dataclasses import dataclass
from uuid import UUID

from apps.privacy.domain.entities import PrivacyErasureRequest
from apps.privacy.domain.errors import PrivacyErasureNotFoundError
from apps.privacy.domain.ports.erasure_request_repository import ErasureRequestRepository


@dataclass(frozen=True, slots=True)
class GetErasureStatus:
    erasures: ErasureRequestRepository

    async def execute(
        self,
        *,
        request_id: UUID,
        subject_user_id: UUID,
    ) -> PrivacyErasureRequest:
        request = await self.erasures.get_by_id(request_id)
        if request is None or request.subject_user_id != subject_user_id:
            raise PrivacyErasureNotFoundError()
        return request
