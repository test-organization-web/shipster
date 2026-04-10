from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.organizations.domain.entities import Organization
from apps.organizations.domain.ports.organization_repository import OrganizationRepository
from apps.organizations.infrastructure.persistence.mappers import (
    organization_domain_to_row,
    organization_row_to_domain,
)
from apps.organizations.infrastructure.persistence.schema.organization import OrganizationORM


class SqlAlchemyOrganizationRepository(OrganizationRepository):
    """PostgreSQL/SQLite-backed repository; inject a scoped ``AsyncSession`` per unit of work."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        row = await self._session.get(OrganizationORM, organization_id)
        return None if row is None else organization_row_to_domain(row)

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(OrganizationORM).where(OrganizationORM.slug == slug).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return None if row is None else organization_row_to_domain(row)

    async def save(self, organization: Organization) -> None:
        existing = await self._session.get(OrganizationORM, organization.id)
        if existing is None:
            self._session.add(organization_domain_to_row(organization))
            return
        existing.name = organization.name
        existing.slug = organization.slug
