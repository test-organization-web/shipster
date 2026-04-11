from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.privacy.domain.entities import (
    PrivacyExportLifecycleEvent,
    PrivacyExportLifecycleEventType,
    PrivacyExportRequest,
    PrivacyExportStatus,
)
from apps.privacy.domain.ports.export_request_repository import ExportRequestRepository
from apps.privacy.infrastructure.persistence.schema.privacy_export_lifecycle_event import (
    PrivacyExportLifecycleEventORM,
)
from apps.privacy.infrastructure.persistence.schema.privacy_export_request import (
    PrivacyExportRequestORM,
)


def _row_to_domain(row: PrivacyExportRequestORM) -> PrivacyExportRequest:
    return PrivacyExportRequest(
        id=row.id,
        subject_user_id=row.subject_user_id,
        status=PrivacyExportStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        expires_at=row.expires_at,
        artifact_key=row.artifact_key,
        failure_reason=row.failure_reason,
    )


def _domain_to_row(request: PrivacyExportRequest) -> PrivacyExportRequestORM:
    return PrivacyExportRequestORM(
        id=request.id,
        subject_user_id=request.subject_user_id,
        status=request.status.value,
        created_at=request.created_at,
        updated_at=request.updated_at,
        expires_at=request.expires_at,
        artifact_key=request.artifact_key,
        failure_reason=request.failure_reason,
    )


def _lifecycle_event_row_to_domain(
    row: PrivacyExportLifecycleEventORM,
) -> PrivacyExportLifecycleEvent:
    return PrivacyExportLifecycleEvent(
        id=row.id,
        export_request_id=row.export_request_id,
        event_type=PrivacyExportLifecycleEventType(row.event_type),
        occurred_at=row.occurred_at,
        actor_user_id=row.actor_user_id,
    )


def _lifecycle_event_types_to_persist(
    *,
    old_status: PrivacyExportStatus | None,
    new_status: PrivacyExportStatus,
    is_insert: bool,
) -> list[PrivacyExportLifecycleEventType]:
    if is_insert:
        if new_status is PrivacyExportStatus.PENDING:
            return [PrivacyExportLifecycleEventType.EXPORT_REQUEST_CREATED]
        return []
    if old_status is None or old_status == new_status:
        return []
    transition = (old_status, new_status)
    if transition == (PrivacyExportStatus.PENDING, PrivacyExportStatus.PROCESSING):
        return [PrivacyExportLifecycleEventType.EXPORT_PROCESSING_STARTED]
    if transition == (PrivacyExportStatus.PROCESSING, PrivacyExportStatus.READY):
        return [PrivacyExportLifecycleEventType.EXPORT_READY]
    if transition == (PrivacyExportStatus.PROCESSING, PrivacyExportStatus.FAILED):
        return [PrivacyExportLifecycleEventType.EXPORT_FAILED]
    if transition == (PrivacyExportStatus.READY, PrivacyExportStatus.EXPIRED):
        return [PrivacyExportLifecycleEventType.EXPORT_EXPIRED]
    if transition == (PrivacyExportStatus.READY, PrivacyExportStatus.FAILED):
        return [PrivacyExportLifecycleEventType.EXPORT_FAILED]
    return []


def _append_lifecycle_event_rows(
    session: AsyncSession,
    *,
    export_request_id: UUID,
    event_types: list[PrivacyExportLifecycleEventType],
    occurred_at: datetime,
    actor_user_id: UUID | None,
) -> None:
    for event_type in event_types:
        session.add(
            PrivacyExportLifecycleEventORM(
                id=uuid4(),
                export_request_id=export_request_id,
                event_type=event_type.value,
                occurred_at=occurred_at,
                actor_user_id=actor_user_id,
            ),
        )


class SqlAlchemyExportRequestRepository(ExportRequestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, request_id: UUID) -> PrivacyExportRequest | None:
        row = await self._session.get(PrivacyExportRequestORM, request_id)
        return None if row is None else _row_to_domain(row)

    async def save(self, request: PrivacyExportRequest) -> None:
        existing = await self._session.get(PrivacyExportRequestORM, request.id)
        occurred_at = request.updated_at
        actor_user_id = request.subject_user_id

        if existing is None:
            self._session.add(_domain_to_row(request))
            # Flush the parent row before inserting lifecycle events. Without an ORM
            # relationship, a single flush may emit child INSERTs first and violate FK.
            await self._session.flush()
            event_types = _lifecycle_event_types_to_persist(
                old_status=None,
                new_status=request.status,
                is_insert=True,
            )
            _append_lifecycle_event_rows(
                self._session,
                export_request_id=request.id,
                event_types=event_types,
                occurred_at=occurred_at,
                actor_user_id=actor_user_id,
            )
            await self._session.flush()
            return

        old_status = PrivacyExportStatus(existing.status)
        existing.status = request.status.value
        existing.updated_at = request.updated_at
        existing.expires_at = request.expires_at
        existing.artifact_key = request.artifact_key
        existing.failure_reason = request.failure_reason

        event_types = _lifecycle_event_types_to_persist(
            old_status=old_status,
            new_status=request.status,
            is_insert=False,
        )
        _append_lifecycle_event_rows(
            self._session,
            export_request_id=request.id,
            event_types=event_types,
            occurred_at=occurred_at,
            actor_user_id=actor_user_id,
        )
        await self._session.flush()

    async def list_pending(self, *, limit: int) -> list[PrivacyExportRequest]:
        stmt = (
            select(PrivacyExportRequestORM)
            .where(PrivacyExportRequestORM.status == PrivacyExportStatus.PENDING.value)
            .order_by(PrivacyExportRequestORM.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_row_to_domain(row) for row in result.scalars().all()]

    async def list_ready(self, *, limit: int) -> list[PrivacyExportRequest]:
        stmt = (
            select(PrivacyExportRequestORM)
            .where(PrivacyExportRequestORM.status == PrivacyExportStatus.READY.value)
            .order_by(
                PrivacyExportRequestORM.expires_at.asc(), PrivacyExportRequestORM.updated_at.asc()
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_row_to_domain(row) for row in result.scalars().all()]

    async def list_lifecycle_events(
        self,
        *,
        export_request_id: UUID,
        limit: int,
        offset: int,
    ) -> list[PrivacyExportLifecycleEvent]:
        stmt = (
            select(PrivacyExportLifecycleEventORM)
            .where(PrivacyExportLifecycleEventORM.export_request_id == export_request_id)
            .order_by(
                PrivacyExportLifecycleEventORM.occurred_at.asc(),
                PrivacyExportLifecycleEventORM.id.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [_lifecycle_event_row_to_domain(row) for row in result.scalars().all()]

    async def count_lifecycle_events(self, *, export_request_id: UUID) -> int:
        stmt = select(func.count(PrivacyExportLifecycleEventORM.id)).where(
            PrivacyExportLifecycleEventORM.export_request_id == export_request_id,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def list_all_for_subject_user(self, subject_user_id: UUID) -> list[PrivacyExportRequest]:
        stmt = (
            select(PrivacyExportRequestORM)
            .where(PrivacyExportRequestORM.subject_user_id == subject_user_id)
            .order_by(PrivacyExportRequestORM.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [_row_to_domain(row) for row in result.scalars().all()]
