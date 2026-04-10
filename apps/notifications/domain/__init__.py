"""Domain types for outbound notifications."""

from apps.notifications.domain.entities import (
    Notification,
    NotificationChannel,
    NotificationMessage,
    NotificationRecipient,
)

__all__ = [
    "Notification",
    "NotificationChannel",
    "NotificationMessage",
    "NotificationRecipient",
]
