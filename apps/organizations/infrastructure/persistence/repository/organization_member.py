from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.organizations.domain.entities import OrganizationMember
from apps.organizations.domain.ports.organization_member_repository import (
    OrganizationMemberRepository,
)
from apps.organizations.infrastructure.persistence.mappers import (
    organization_member_domain_to_row,
    organization_member_row_to_domain,
)
from apps.organizations.infrastructure.persistence.schema.organization_member import (
    OrganizationMemberORM,
)


class SqlAlchemyOrganizationMemberRepository(OrganizationMemberRepository):
    """PostgreSQL/SQLite-backed repository; inject a scoped ``AsyncSession`` per unit of work."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_organization(self, organization_id: UUID) -> list[OrganizationMember]:
        stmt = (
            select(OrganizationMemberORM)
            .where(OrganizationMemberORM.organization_id == organization_id)
            .order_by(OrganizationMemberORM.id)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [organization_member_row_to_domain(row) for row in rows]

    async def count_by_user(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(OrganizationMemberORM)
            .where(OrganizationMemberORM.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def list_by_user(self, user_id: UUID) -> list[OrganizationMember]:
        stmt = (
            select(OrganizationMemberORM)
            .where(OrganizationMemberORM.user_id == user_id)
            .order_by(OrganizationMemberORM.id)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [organization_member_row_to_domain(row) for row in rows]

    async def find_by_organization_and_user(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> OrganizationMember | None:
        stmt = (
            select(OrganizationMemberORM)
            .where(
                OrganizationMemberORM.organization_id == organization_id,
                OrganizationMemberORM.user_id == user_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return None if row is None else organization_member_row_to_domain(row)

    async def save(self, member: OrganizationMember) -> None:
        existing = await self._session.get(OrganizationMemberORM, member.id)
        if existing is None:
            self._session.add(organization_member_domain_to_row(member))
            return
        existing.organization_id = member.organization_id
        existing.user_id = member.user_id
