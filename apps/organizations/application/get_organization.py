from uuid import UUID

from apps.organizations.domain.entities import Organization
from apps.organizations.domain.errors import OrganizationNotFoundError
from apps.organizations.domain.ports.organization_repository import OrganizationRepository


class GetOrganizationById:
    """Load an organization by id."""

    def __init__(self, organizations: OrganizationRepository) -> None:
        self._organizations = organizations

    async def execute(self, organization_id: UUID) -> Organization:
        organization = await self._organizations.get_by_id(organization_id)
        if organization is None:
            raise OrganizationNotFoundError(str(organization_id))
        return organization
