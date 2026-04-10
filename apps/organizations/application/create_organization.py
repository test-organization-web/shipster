from uuid import UUID, uuid4

from apps.organizations.domain.entities import Organization, OrganizationMember
from apps.organizations.domain.errors import SlugAlreadyTakenError
from apps.organizations.domain.ports.organization_member_repository import (
    OrganizationMemberRepository,
)
from apps.organizations.domain.ports.organization_repository import OrganizationRepository
from apps.users.domain.errors import UserNotFoundError
from apps.users.domain.ports.user_repository import UserRepository


class CreateOrganization:
    """Register a new organization with a unique slug and add the creator as a member."""

    def __init__(
        self,
        organizations: OrganizationRepository,
        members: OrganizationMemberRepository,
        users: UserRepository,
    ) -> None:
        self._organizations = organizations
        self._members = members
        self._users = users

    async def execute(self, *, name: str, slug: str, creator_user_id: UUID) -> Organization:
        user = await self._users.get_by_id(creator_user_id)
        if user is None:
            raise UserNotFoundError(str(creator_user_id))

        normalized_name = name.strip()
        normalized_slug = slug.strip().lower()
        if await self._organizations.get_by_slug(normalized_slug) is not None:
            raise SlugAlreadyTakenError(normalized_slug)
        organization = Organization(
            id=uuid4(),
            name=normalized_name,
            slug=normalized_slug,
        )
        await self._organizations.save(organization)
        await self._members.save(
            OrganizationMember(
                id=uuid4(),
                organization_id=organization.id,
                user_id=creator_user_id,
            ),
        )
        return organization
