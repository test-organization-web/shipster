from typing import Protocol
from uuid import UUID

from apps.organizations.domain.entities import OrganizationInvitation


class OrganizationInvitationRepository(Protocol):
    async def find_by_token_hash(self, token_hash: str) -> OrganizationInvitation | None:
        """Return invitation by hashed token, if any."""

    async def count_by_email(self, email: str) -> int:
        """Return how many invitations target the normalized email."""

    async def list_by_email(self, email: str) -> list[OrganizationInvitation]:
        """Return invitations addressed to the normalized email."""

    async def find_pending_by_organization_and_email(
        self,
        organization_id: UUID,
        email: str,
    ) -> OrganizationInvitation | None:
        """Return a pending invitation for the org and normalized email."""

    async def save(self, invitation: OrganizationInvitation) -> None:
        """Persist new or updated invitation."""

    async def delete_all_for_email(self, email: str) -> int:
        """Delete invitations matching the normalized email; return rows deleted."""
