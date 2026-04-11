from uuid import UUID

from apps.organizations.domain.ports.organization_data_exporter import OrganizationDataExporter
from apps.organizations.domain.ports.organization_invitation_repository import (
    OrganizationInvitationRepository,
)
from apps.organizations.domain.ports.organization_member_repository import (
    OrganizationMemberRepository,
)
from apps.users.domain.errors import UserNotFoundError
from apps.users.domain.ports.user_repository import UserRepository


class RepositoryOrganizationDataExporter(OrganizationDataExporter):
    def __init__(
        self,
        *,
        members: OrganizationMemberRepository,
        invitations: OrganizationInvitationRepository,
        users: UserRepository,
    ) -> None:
        self._members = members
        self._invitations = invitations
        self._users = users

    async def export_for_user(self, user_id: UUID) -> dict[str, object]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        memberships = await self._members.list_by_user(user_id)
        invitations = await self._invitations.list_by_email(user.email)
        return {
            "memberships": [
                {
                    "id": str(member.id),
                    "organization_id": str(member.organization_id),
                    "user_id": str(member.user_id),
                }
                for member in memberships
            ],
            "invitations": [
                {
                    "id": str(invitation.id),
                    "organization_id": str(invitation.organization_id),
                    "email": invitation.email,
                    "status": invitation.status.value,
                    "created_at": invitation.created_at.isoformat(),
                    "expires_at": invitation.expires_at.isoformat(),
                }
                for invitation in invitations
            ],
        }
