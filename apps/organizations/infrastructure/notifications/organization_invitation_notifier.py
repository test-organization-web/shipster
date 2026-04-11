from apps.notifications.domain.entities import (
    Notification,
    NotificationChannel,
    NotificationMessage,
    NotificationRecipient,
)
from apps.notifications.domain.ports.notification_sender import NotificationSender
from apps.organizations.domain.invitation_notification import OrganizationInvitationNotification
from apps.organizations.domain.ports.organization_invitation_notifier import (
    OrganizationInvitationNotifier,
)


class NotificationSenderOrganizationInvitationNotifier(OrganizationInvitationNotifier):
    def __init__(
        self,
        sender: NotificationSender,
        *,
        accept_url_template: str | None = None,
    ) -> None:
        self._sender = sender
        self._accept_url_template = accept_url_template

    async def send_invitation(self, notification: OrganizationInvitationNotification) -> None:
        accept_url = self._build_accept_url(notification)
        if accept_url is None:
            text_body = (
                f"You have been invited to join {notification.organization_name}. "
                f"Invitation token: {notification.token}. "
                f"Expires at: {notification.expires_at.isoformat()}."
            )
        else:
            text_body = (
                f"You have been invited to join {notification.organization_name}. "
                f"Accept invitation: {accept_url}. "
                f"Expires at: {notification.expires_at.isoformat()}."
            )
        await self._sender.send(
            Notification(
                channel=NotificationChannel.EMAIL,
                recipient=NotificationRecipient(email=notification.email),
                message=NotificationMessage(
                    subject=f"Invitation to join {notification.organization_name}",
                    text_body=text_body,
                ),
            )
        )

    def _build_accept_url(self, notification: OrganizationInvitationNotification) -> str | None:
        template = self._accept_url_template
        if template is None or not template.strip():
            return None
        return template.format(
            token=notification.token,
            organization_id=notification.organization_id,
        )
