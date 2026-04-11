from uuid import UUID

from apps.organizations.domain.ports.organization_invitation_repository import (
    OrganizationInvitationRepository,
)
from apps.users.domain.ports.user_repository import UserRepository


class OrganizationInvitationsSubjectDataEraser:
    """Remove organization invitations addressed at the subject's email (pre-anonymize)."""

    def __init__(
        self,
        *,
        users: UserRepository,
        invitations: OrganizationInvitationRepository,
    ) -> None:
        self._users = users
        self._invitations = invitations

    async def erase_for_user(self, user_id: UUID) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            return
        await self._invitations.delete_all_for_email(user.email)
