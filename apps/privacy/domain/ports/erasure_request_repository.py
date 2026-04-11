from typing import Protocol
from uuid import UUID

from apps.privacy.domain.entities import PrivacyErasureRequest


class ErasureRequestRepository(Protocol):
    async def get_by_id(self, request_id: UUID) -> PrivacyErasureRequest | None:
        """Return erasure request by id."""

    async def save(self, request: PrivacyErasureRequest) -> None:
        """Persist new or updated erasure request."""

    async def find_active_for_subject(self, subject_user_id: UUID) -> PrivacyErasureRequest | None:
        """Return a pending or processing erasure request for the subject, if any."""

    async def list_pending(self, *, limit: int) -> list[PrivacyErasureRequest]:
        """Return pending erasure requests, oldest first."""
