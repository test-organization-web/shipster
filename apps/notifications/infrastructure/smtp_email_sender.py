"""SMTP-backed email sender."""

from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr

import aiosmtplib

from apps.notifications.domain.entities import Notification
from apps.notifications.domain.ports import NotificationSender


@dataclass(frozen=True, slots=True)
class SmtpNotificationSettings:
    host: str
    port: int
    username: str | None
    password: str | None
    use_tls: bool
    start_tls: bool
    timeout_seconds: float
    default_from_email: str
    default_from_name: str | None = None


class SmtpEmailSender(NotificationSender):
    def __init__(self, settings: SmtpNotificationSettings) -> None:
        self._settings = settings

    async def send(self, notification: Notification) -> None:
        recipient_email = notification.recipient.email
        if recipient_email is None or not recipient_email.strip():
            raise ValueError("Email notifications require recipient.email")
        message = EmailMessage()
        message["From"] = formataddr(
            (
                notification.sender_name or self._settings.default_from_name or "",
                notification.sender_email or self._settings.default_from_email,
            ),
        )
        message["To"] = formataddr(
            (
                notification.recipient.name or "",
                recipient_email,
            ),
        )
        message["Subject"] = notification.message.subject
        if notification.reply_to:
            message["Reply-To"] = notification.reply_to
        message.set_content(notification.message.text_body)
        if notification.message.html_body is not None:
            message.add_alternative(notification.message.html_body, subtype="html")
        await aiosmtplib.send(
            message,
            hostname=self._settings.host,
            port=self._settings.port,
            username=self._settings.username,
            password=self._settings.password,
            use_tls=self._settings.use_tls,
            start_tls=self._settings.start_tls,
            timeout=self._settings.timeout_seconds,
        )
