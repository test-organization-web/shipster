"""Route notifications to the currently implemented delivery channels."""

from apps.notifications.domain.entities import Notification, NotificationChannel
from apps.notifications.domain.ports.notification_sender import (
    EmailSender,
    NotificationSender,
    TelegramSender,
)


class SendNotification(NotificationSender):
    """Route each notification to exactly one channel adapter."""

    def __init__(
        self,
        email_sender: EmailSender,
        telegram_sender: TelegramSender,
    ) -> None:
        self._email_sender = email_sender
        self._telegram_sender = telegram_sender

    async def send(self, notification: Notification) -> None:
        match notification.channel:
            case NotificationChannel.EMAIL:
                await self._email_sender.send(notification)
            case NotificationChannel.TELEGRAM:
                await self._telegram_sender.send(notification)
            case _:
                msg = f"Unsupported notification channel: {notification.channel!r}"
                raise ValueError(msg)
