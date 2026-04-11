import html
import logging

from apps.notifications.domain.entities import (
    Notification,
    NotificationChannel,
    NotificationMessage,
    NotificationRecipient,
)
from apps.notifications.domain.ports.notification_sender import NotificationSender
from apps.users.domain.ports.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from apps.users.domain.ports.user_repository import UserRepository

_LOG = logging.getLogger(__name__)


class ProcessPasswordResetNotifications:
    """Deliver emails for PENDING reset rows (plaintext cleared after send)."""

    def __init__(
        self,
        *,
        reset_tokens: PasswordResetTokenRepository,
        users: UserRepository,
        notification_sender: NotificationSender,
        password_reset_url_template: str | None,
    ) -> None:
        self._reset_tokens = reset_tokens
        self._users = users
        self._notification_sender = notification_sender
        self._password_reset_url_template = password_reset_url_template

    async def execute(self, *, limit: int) -> None:
        pending = await self._reset_tokens.list_pending_notifications(limit=limit)
        for item in pending:
            user = await self._users.get_by_id(item.user_id)
            if user is None:
                _LOG.warning(
                    "password reset delivery skipped: user missing",
                    extra={"token_id": str(item.token_id), "user_id": str(item.user_id)},
                )
                continue
            reset_link = (
                self._password_reset_url_template.format(token=item.plain_token)
                if self._password_reset_url_template
                else None
            )
            text_body = (
                f"Use this link to reset your password:\n{reset_link}\n"
                if reset_link
                else f"Use this password reset token:\n{item.plain_token}\n"
            )
            html_link = html.escape(reset_link) if reset_link else None
            html_token = html.escape(item.plain_token)
            html_body = (
                f'<p><a href="{html_link}">Reset your password</a></p>'
                if html_link
                else f"<p>Password reset token: <code>{html_token}</code></p>"
            )
            await self._notification_sender.send(
                Notification(
                    channel=NotificationChannel.EMAIL,
                    recipient=NotificationRecipient(email=user.email),
                    message=NotificationMessage(
                        subject="Password reset",
                        text_body=text_body,
                        html_body=html_body,
                    ),
                ),
            )
            await self._reset_tokens.mark_notified_and_clear_pending_plain_token(item.token_id)
