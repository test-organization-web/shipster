"""Telegram Bot API delivery adapter."""

from dataclasses import dataclass

import httpx

from apps.notifications.domain.entities import Notification
from apps.notifications.domain.ports import NotificationSender


@dataclass(frozen=True, slots=True)
class TelegramNotificationSettings:
    bot_token: str | None
    base_url: str
    timeout_seconds: float


class TelegramSenderHttpApi(NotificationSender):
    def __init__(self, settings: TelegramNotificationSettings) -> None:
        self._settings = settings

    async def send(self, notification: Notification) -> None:
        chat_id = notification.recipient.telegram_chat_id
        if chat_id is None or not chat_id.strip():
            raise ValueError("Telegram notifications require recipient.telegram_chat_id")
        bot_token = self._settings.bot_token
        if bot_token is None or not bot_token.strip():
            raise ValueError("Telegram delivery requires SHIPSTER_TELEGRAM_BOT_TOKEN")
        async with httpx.AsyncClient(
            base_url=self._settings.base_url.rstrip("/"),
            timeout=self._settings.timeout_seconds,
        ) as client:
            response = await client.post(
                f"/bot{bot_token.strip()}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": notification.message.text_body,
                },
            )
            response.raise_for_status()
