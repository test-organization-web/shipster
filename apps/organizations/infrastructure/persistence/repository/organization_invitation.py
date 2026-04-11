from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.organizations.domain.entities import InvitationStatus, OrganizationInvitation
from apps.organizations.domain.ports.organization_invitation_repository import (
    OrganizationInvitationRepository,
)
from apps.organizations.infrastructure.persistence.mappers import (
    organization_invitation_domain_to_row,
    organization_invitation_row_to_domain,
)
from apps.organizations.infrastructure.persistence.schema.organization_invitation import (
    OrganizationInvitationORM,
)


class SqlAlchemyOrganizationInvitationRepository(OrganizationInvitationRepository):
    """SQLAlchemy-backed invitation store; inject a scoped ``AsyncSession`` per unit of work."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_token_hash(self, token_hash: str) -> OrganizationInvitation | None:
        stmt = select(OrganizationInvitationORM).where(
            OrganizationInvitationORM.token_hash == token_hash,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return None if row is None else organization_invitation_row_to_domain(row)

    async def count_by_email(self, email: str) -> int:
        stmt = (
            select(func.count())
            .select_from(OrganizationInvitationORM)
            .where(OrganizationInvitationORM.email == email)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def list_by_email(self, email: str) -> list[OrganizationInvitation]:
        stmt = (
            select(OrganizationInvitationORM)
            .where(OrganizationInvitationORM.email == email)
            .order_by(OrganizationInvitationORM.id)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [organization_invitation_row_to_domain(row) for row in rows]

    async def find_pending_by_organization_and_email(
        self,
        organization_id: UUID,
        email: str,
    ) -> OrganizationInvitation | None:
        stmt = (
            select(OrganizationInvitationORM)
            .where(
                OrganizationInvitationORM.organization_id == organization_id,
                OrganizationInvitationORM.email == email,
                OrganizationInvitationORM.status == InvitationStatus.PENDING.value,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return None if row is None else organization_invitation_row_to_domain(row)

    async def save(self, invitation: OrganizationInvitation) -> None:
        existing = await self._session.get(OrganizationInvitationORM, invitation.id)
        if existing is None:
            self._session.add(organization_invitation_domain_to_row(invitation))
            return
        existing.organization_id = invitation.organization_id
        existing.email = invitation.email
        existing.token_hash = invitation.token_hash
        existing.invited_by_user_id = invitation.invited_by_user_id
        existing.created_at = invitation.created_at
        existing.expires_at = invitation.expires_at
        existing.accepted_at = invitation.accepted_at
        existing.status = invitation.status.value

    async def delete_all_for_email(self, email: str) -> int:
        stmt = delete(OrganizationInvitationORM).where(OrganizationInvitationORM.email == email)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount or 0)
