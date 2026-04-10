from typing import Protocol
from uuid import UUID

from apps.organizations.domain.entities import OrganizationMember


class OrganizationMemberRepository(Protocol):
    async def list_by_organization(self, organization_id: UUID) -> list[OrganizationMember]:
        """Return all memberships for an organization."""

    async def find_by_organization_and_user(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> OrganizationMember | None:
        """Return membership if it exists."""

    async def save(self, member: OrganizationMember) -> None:
        """Persist new or updated membership."""
