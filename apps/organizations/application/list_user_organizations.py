from dataclasses import dataclass
from uuid import UUID

from apps.organizations.domain.ports.organization_member_repository import (
    OrganizationMemberRepository,
)
from apps.organizations.domain.ports.organization_repository import OrganizationRepository


@dataclass(frozen=True, slots=True)
class UserOrganizationSummary:
    organization_id: UUID
    organization_name: str


class ListUserOrganizations:
    """List organizations the user is a member of."""

    def __init__(
        self,
        organizations: OrganizationRepository,
        members: OrganizationMemberRepository,
    ) -> None:
        self._organizations = organizations
        self._members = members

    async def execute(self, user_id: UUID) -> list[UserOrganizationSummary]:
        memberships = await self._members.list_by_user(user_id)
        result: list[UserOrganizationSummary] = []
        for membership in memberships:
            org = await self._organizations.get_by_id(membership.organization_id)
            if org is None:
                continue
            result.append(
                UserOrganizationSummary(
                    organization_id=org.id,
                    organization_name=org.name,
                )
            )
        return result
