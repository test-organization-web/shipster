"""Composition-root adapter from organization invitation events to notifications."""

from apps.notifications.domain.entities import (
    Notification,
    NotificationChannel,
    NotificationMessage,
    NotificationRecipient,
)
from apps.notifications.domain.ports.notification_sender import NotificationSender
from apps.organizations.domain.organization_public_events import (
    OrganizationInvitationCreatedPayload,
)
from apps.organizations.domain.ports.organization_invitation_created_handler import (
    OrganizationInvitationCreatedHandler,
)


class OrganizationInvitationCreatedEmailHandler(OrganizationInvitationCreatedHandler):
    """Translate the organizations event contract into the notifications use case."""

    def __init__(self, sender: NotificationSender) -> None:
        self._sender = sender

    async def handle(self, payload: OrganizationInvitationCreatedPayload) -> None:
        await self._sender.send(
            Notification(
                channel=NotificationChannel.EMAIL,
                recipient=NotificationRecipient(email=payload.email),
                message=NotificationMessage(
                    subject=f"Invitation to join {payload.organization_name}",
                    text_body=(
                        f"You have been invited to join {payload.organization_name}. "
                        f"Invitation token: {payload.token}. "
                        f"Expires at: {payload.expires_at.isoformat()}."
                    ),
                ),
            ),
        )
