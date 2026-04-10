"""Build shared messaging ports from configuration."""

import threading

from apps.messaging.domain.ports.messaging import MessagePublisher, MessageReceiver
from apps.messaging.infrastructure.rabbitmq_messaging import RabbitMqMessaging
from apps.messaging.infrastructure.redis_streams import RedisStreamMessaging
from shipster.platform.redis_client import get_async_redis
from shipster.platform.settings import get_global_settings

_lock = threading.Lock()
_redis_messaging: RedisStreamMessaging | None = None
_rabbit_messaging: RabbitMqMessaging | None = None


def _get_redis_messaging() -> RedisStreamMessaging:
    global _redis_messaging
    if _redis_messaging is None:
        with _lock:
            if _redis_messaging is None:
                _redis_messaging = RedisStreamMessaging(get_async_redis())
    return _redis_messaging


def _get_rabbit_messaging() -> RabbitMqMessaging:
    global _rabbit_messaging
    if _rabbit_messaging is None:
        with _lock:
            if _rabbit_messaging is None:
                url = get_global_settings().rabbitmq_url
                if url is None or not str(url).strip():
                    msg = (
                        "MESSAGING_BACKEND=rabbitmq requires SHIPSTER_RABBITMQ_URL or RABBITMQ_URL"
                    )
                    raise ValueError(msg)
                _rabbit_messaging = RabbitMqMessaging(str(url).strip())
    return _rabbit_messaging


def _messaging_impl() -> RedisStreamMessaging | RabbitMqMessaging:
    backend = get_global_settings().messaging_backend.strip().lower()
    match backend:
        case "redis":
            return _get_redis_messaging()
        case "rabbitmq":
            return _get_rabbit_messaging()
        case _:
            supported = "redis, rabbitmq"
            msg = f"Unsupported MESSAGING_BACKEND={backend!r}; supported: {supported}"
            raise ValueError(msg)


def create_message_publisher() -> MessagePublisher:
    """Build the process-wide publisher (``MESSAGING_BACKEND`` env, default ``redis``)."""
    return _messaging_impl()


def create_message_receiver() -> MessageReceiver:
    """Build the process-wide receiver (same backend and adapter instance as publisher)."""
    return _messaging_impl()
