"""Core notification value objects."""

from dataclasses import dataclass
from enum import StrEnum


class NotificationChannel(StrEnum):
    EMAIL = "email"
    TELEGRAM = "telegram"


@dataclass(frozen=True, slots=True)
class NotificationRecipient:
    email: str | None = None
    telegram_chat_id: str | None = None
    name: str | None = None


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    subject: str
    text_body: str
    html_body: str | None = None


@dataclass(frozen=True, slots=True)
class Notification:
    channel: NotificationChannel
    recipient: NotificationRecipient
    message: NotificationMessage
    sender_email: str | None = None
    sender_name: str | None = None
    reply_to: str | None = None
