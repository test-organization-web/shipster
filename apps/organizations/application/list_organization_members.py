from uuid import UUID

from apps.organizations.domain.entities import OrganizationMember
from apps.organizations.domain.errors import OrganizationNotFoundError
from apps.organizations.domain.ports.organization_member_repository import (
    OrganizationMemberRepository,
)
from apps.organizations.domain.ports.organization_repository import OrganizationRepository


class ListOrganizationMembers:
    """List all members of an organization."""

    def __init__(
        self,
        organizations: OrganizationRepository,
        members: OrganizationMemberRepository,
    ) -> None:
        self._organizations = organizations
        self._members = members

    async def execute(self, organization_id: UUID) -> list[OrganizationMember]:
        if await self._organizations.get_by_id(organization_id) is None:
            raise OrganizationNotFoundError(str(organization_id))
        return await self._members.list_by_organization(organization_id)
