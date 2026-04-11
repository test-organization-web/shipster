from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.domain.entities import (
    PasswordResetPendingNotification,
    UserPasswordResetTokenStatus,
)
from apps.users.domain.ports.password_reset_token_repository import PasswordResetTokenRepository
from apps.users.infrastructure.persistence.schema.user_password_reset_token import (
    UserPasswordResetTokenORM,
)


class SqlAlchemyPasswordResetTokenRepository(PasswordResetTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def revoke_active_for_user(self, user_id: UUID) -> None:
        await self._session.execute(
            update(UserPasswordResetTokenORM)
            .where(
                UserPasswordResetTokenORM.user_id == user_id,
                UserPasswordResetTokenORM.status.in_(
                    (
                        UserPasswordResetTokenStatus.PENDING.value,
                        UserPasswordResetTokenStatus.NOTIFIED.value,
                    ),
                ),
            )
            .values(status=UserPasswordResetTokenStatus.REVOKED.value),
        )

    async def delete_all_for_user(self, user_id: UUID) -> None:
        await self._session.execute(
            delete(UserPasswordResetTokenORM).where(UserPasswordResetTokenORM.user_id == user_id),
        )

    async def save(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        pending_plain_token: str | None = None,
        status: UserPasswordResetTokenStatus = UserPasswordResetTokenStatus.PENDING,
    ) -> UUID:
        token_id = uuid4()
        self._session.add(
            UserPasswordResetTokenORM(
                id=token_id,
                user_id=user_id,
                token_hash=token_hash,
                pending_plain_token=pending_plain_token,
                status=status.value,
                expires_at=expires_at,
                created_at=datetime.now(UTC),
            ),
        )
        return token_id

    async def list_pending_notifications(
        self,
        *,
        limit: int,
    ) -> list[PasswordResetPendingNotification]:
        stmt = (
            select(
                UserPasswordResetTokenORM.id,
                UserPasswordResetTokenORM.user_id,
                UserPasswordResetTokenORM.pending_plain_token,
            )
            .where(
                UserPasswordResetTokenORM.status == UserPasswordResetTokenStatus.PENDING.value,
                UserPasswordResetTokenORM.pending_plain_token.is_not(None),
            )
            .order_by(UserPasswordResetTokenORM.created_at.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            PasswordResetPendingNotification(
                token_id=r[0],
                user_id=r[1],
                plain_token=r[2],
            )
            for r in rows
        ]

    async def mark_notified_and_clear_pending_plain_token(self, token_id: UUID) -> bool:
        result = await self._session.execute(
            update(UserPasswordResetTokenORM)
            .where(
                UserPasswordResetTokenORM.id == token_id,
                UserPasswordResetTokenORM.status == UserPasswordResetTokenStatus.PENDING.value,
                UserPasswordResetTokenORM.pending_plain_token.is_not(None),
            )
            .values(
                status=UserPasswordResetTokenStatus.NOTIFIED.value,
                pending_plain_token=None,
            ),
        )
        return result.rowcount == 1

    async def mark_notified_if_pending(self, token_id: UUID) -> bool:
        result = await self._session.execute(
            update(UserPasswordResetTokenORM)
            .where(
                UserPasswordResetTokenORM.id == token_id,
                UserPasswordResetTokenORM.status == UserPasswordResetTokenStatus.PENDING.value,
            )
            .values(
                status=UserPasswordResetTokenStatus.NOTIFIED.value,
                pending_plain_token=None,
            ),
        )
        return result.rowcount == 1

    async def find_valid_notified_by_token_hash(
        self,
        *,
        token_hash: str,
        at: datetime,
    ) -> tuple[UUID, UUID] | None:
        stmt = (
            select(UserPasswordResetTokenORM.id, UserPasswordResetTokenORM.user_id)
            .where(
                UserPasswordResetTokenORM.token_hash == token_hash,
                UserPasswordResetTokenORM.status == UserPasswordResetTokenStatus.NOTIFIED.value,
                UserPasswordResetTokenORM.expires_at > at,
            )
            .limit(1)
        )
        row = (await self._session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return (row[0], row[1])

    async def mark_used_if_notified(self, token_id: UUID) -> bool:
        result = await self._session.execute(
            update(UserPasswordResetTokenORM)
            .where(
                UserPasswordResetTokenORM.id == token_id,
                UserPasswordResetTokenORM.status == UserPasswordResetTokenStatus.NOTIFIED.value,
            )
            .values(status=UserPasswordResetTokenStatus.USED.value),
        )
        return result.rowcount == 1
