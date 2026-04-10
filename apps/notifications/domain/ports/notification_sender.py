from typing import Protocol

from apps.notifications.domain.entities import Notification


class NotificationSender(Protocol):
    async def send(self, notification: Notification) -> None:
        """Dispatch a notification through its configured channel."""


class EmailSender(Protocol):
    async def send(self, notification: Notification) -> None:
        """Dispatch a notification through its configured channel."""


class TelegramSender(Protocol):
    async def send(self, notification: Notification) -> None:
        """Dispatch a notification through its configured channel."""
