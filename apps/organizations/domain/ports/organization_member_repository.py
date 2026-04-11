from typing import Protocol
from uuid import UUID

from apps.organizations.domain.entities import OrganizationMember


class OrganizationMemberRepository(Protocol):
    async def list_by_organization(self, organization_id: UUID) -> list[OrganizationMember]:
        """Return all memberships for an organization."""

    async def count_by_user(self, user_id: UUID) -> int:
        """Return how many memberships the user has."""

    async def list_by_user(self, user_id: UUID) -> list[OrganizationMember]:
        """Return all memberships for the given user."""

    async def find_by_organization_and_user(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> OrganizationMember | None:
        """Return membership if it exists."""

    async def save(self, member: OrganizationMember) -> None:
        """Persist new or updated membership."""
