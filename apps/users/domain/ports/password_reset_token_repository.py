from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from apps.users.domain.entities import (
    PasswordResetPendingNotification,
    UserPasswordResetTokenStatus,
)


class PasswordResetTokenRepository(Protocol):
    """Opaque reset tokens (stored hashed); used to validate a future reset confirmation."""

    async def revoke_active_for_user(self, user_id: UUID) -> None:
        """Mark pending/notified tokens revoked (superseded by a new request)."""

    async def delete_all_for_user(self, user_id: UUID) -> None:
        """Remove every token row for the user (e.g. GDPR erasure)."""

    async def save(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        pending_plain_token: str | None = None,
        status: UserPasswordResetTokenStatus = UserPasswordResetTokenStatus.PENDING,
    ) -> UUID:
        """Persist a new token (default status: pending); return its id."""

    async def list_pending_notifications(
        self,
        *,
        limit: int,
    ) -> Sequence[PasswordResetPendingNotification]:
        """PENDING rows that still hold a plaintext token for delivery (scheduler)."""

    async def mark_notified_and_clear_pending_plain_token(self, token_id: UUID) -> bool:
        """After successful delivery: NOTIFIED and clear plaintext; return whether updated."""

    async def mark_notified_if_pending(self, token_id: UUID) -> bool:
        """Set status to notified if still pending; return whether a row was updated."""

    async def find_valid_notified_by_token_hash(
        self,
        *,
        token_hash: str,
        at: datetime,
    ) -> tuple[UUID, UUID] | None:
        """Return ``(token_id, user_id)`` for a non-expired notified token, if any."""

    async def mark_used_if_notified(self, token_id: UUID) -> bool:
        """Set status to used if currently notified; return whether a row was updated."""
