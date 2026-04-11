from typing import Protocol

from apps.organizations.domain.invitation_notification import OrganizationInvitationNotification


class OrganizationInvitationNotifier(Protocol):
    async def send_invitation(self, notification: OrganizationInvitationNotification) -> None:
        """Deliver an organization invitation to its recipient."""
