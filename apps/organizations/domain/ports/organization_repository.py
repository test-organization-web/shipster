from typing import Protocol
from uuid import UUID

from apps.organizations.domain.entities import Organization


class OrganizationRepository(Protocol):
    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        """Return organization by primary key."""

    async def get_by_slug(self, slug: str) -> Organization | None:
        """Return organization by normalized slug (lowercase)."""

    async def save(self, organization: Organization) -> None:
        """Persist new or updated organization."""
