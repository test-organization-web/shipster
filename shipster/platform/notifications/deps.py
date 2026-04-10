"""Process-wide notification dependencies."""

import threading

from apps.notifications.application import SendNotification
from apps.notifications.domain.ports.notification_sender import (
    EmailSender,
    NotificationSender,
    TelegramSender,
)
from apps.notifications.infrastructure.smtp_email_sender import (
    SmtpEmailSender,
    SmtpNotificationSettings,
)
from apps.notifications.infrastructure.telegram_sender import (
    TelegramNotificationSettings,
    TelegramSenderHttpApi,
)
from shipster.platform.settings import get_global_settings

_lock = threading.RLock()
_email_sender: EmailSender | None = None
_telegram_sender: TelegramSender | None = None
_notification_sender: NotificationSender | None = None


def ensure_email_sender() -> EmailSender:
    global _email_sender
    if _email_sender is None:
        with _lock:
            if _email_sender is None:
                settings = get_global_settings()
                _email_sender = SmtpEmailSender(
                    SmtpNotificationSettings(
                        host=settings.smtp_host,
                        port=settings.smtp_port,
                        username=settings.smtp_username,
                        password=settings.smtp_password,
                        use_tls=settings.smtp_use_tls,
                        start_tls=settings.smtp_start_tls,
                        timeout_seconds=settings.smtp_timeout_seconds,
                        default_from_email=settings.smtp_default_from_email,
                        default_from_name=settings.smtp_default_from_name,
                    ),
                )
    return _email_sender


def ensure_telegram_sender() -> TelegramSender:
    global _telegram_sender
    if _telegram_sender is None:
        with _lock:
            if _telegram_sender is None:
                settings = get_global_settings()
                _telegram_sender = TelegramSenderHttpApi(
                    TelegramNotificationSettings(
                        bot_token=settings.telegram_bot_token,
                        base_url=settings.telegram_base_url,
                        timeout_seconds=settings.telegram_timeout_seconds,
                    ),
                )
    return _telegram_sender


def ensure_notification_sender() -> NotificationSender:
    global _notification_sender
    if _notification_sender is None:
        with _lock:
            if _notification_sender is None:
                _notification_sender = SendNotification(
                    ensure_email_sender(),
                    ensure_telegram_sender(),
                )
    return _notification_sender


async def get_notification_sender() -> NotificationSender:
    return ensure_notification_sender()
