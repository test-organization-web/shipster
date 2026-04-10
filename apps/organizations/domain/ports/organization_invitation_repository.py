from typing import Protocol
from uuid import UUID

from apps.organizations.domain.entities import OrganizationInvitation


class OrganizationInvitationRepository(Protocol):
    async def find_by_token_hash(self, token_hash: str) -> OrganizationInvitation | None:
        """Return invitation by hashed token, if any."""

    async def find_pending_by_organization_and_email(
        self,
        organization_id: UUID,
        email: str,
    ) -> OrganizationInvitation | None:
        """Return a pending invitation for the org and normalized email."""

    async def save(self, invitation: OrganizationInvitation) -> None:
        """Persist new or updated invitation."""
