from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.privacy.domain.entities import PrivacyErasureRequest, PrivacyErasureStatus
from apps.privacy.domain.ports.erasure_request_repository import ErasureRequestRepository
from apps.privacy.infrastructure.persistence.schema.privacy_erasure_request import (
    PrivacyErasureRequestORM,
)


def _row_to_domain(row: PrivacyErasureRequestORM) -> PrivacyErasureRequest:
    return PrivacyErasureRequest(
        id=row.id,
        subject_user_id=row.subject_user_id,
        status=PrivacyErasureStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        failure_reason=row.failure_reason,
    )


def _domain_to_row(request: PrivacyErasureRequest) -> PrivacyErasureRequestORM:
    return PrivacyErasureRequestORM(
        id=request.id,
        subject_user_id=request.subject_user_id,
        status=request.status.value,
        created_at=request.created_at,
        updated_at=request.updated_at,
        failure_reason=request.failure_reason,
    )


class SqlAlchemyErasureRequestRepository(ErasureRequestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, request_id: UUID) -> PrivacyErasureRequest | None:
        row = await self._session.get(PrivacyErasureRequestORM, request_id)
        return None if row is None else _row_to_domain(row)

    async def save(self, request: PrivacyErasureRequest) -> None:
        existing = await self._session.get(PrivacyErasureRequestORM, request.id)
        if existing is None:
            self._session.add(_domain_to_row(request))
            await self._session.flush()
            return

        existing.status = request.status.value
        existing.updated_at = request.updated_at
        existing.failure_reason = request.failure_reason
        await self._session.flush()

    async def find_active_for_subject(self, subject_user_id: UUID) -> PrivacyErasureRequest | None:
        stmt = (
            select(PrivacyErasureRequestORM)
            .where(
                PrivacyErasureRequestORM.subject_user_id == subject_user_id,
                PrivacyErasureRequestORM.status.in_(
                    (
                        PrivacyErasureStatus.PENDING.value,
                        PrivacyErasureStatus.PROCESSING.value,
                    ),
                ),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return None if row is None else _row_to_domain(row)

    async def list_pending(self, *, limit: int) -> list[PrivacyErasureRequest]:
        stmt = (
            select(PrivacyErasureRequestORM)
            .where(PrivacyErasureRequestORM.status == PrivacyErasureStatus.PENDING.value)
            .order_by(PrivacyErasureRequestORM.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_row_to_domain(row) for row in result.scalars().all()]
