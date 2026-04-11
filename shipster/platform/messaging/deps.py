"""FastAPI dependencies for shared messaging ports."""

import threading

from apps.messaging.domain.ports.messaging import MessagePublisher, MessageReceiver
from apps.messaging.factory import create_message_publisher, create_message_receiver

_lock = threading.RLock()
_publisher: MessagePublisher | None = None
_receiver: MessageReceiver | None = None


def ensure_message_publisher() -> MessagePublisher:
    """Lazy singleton (sync); use from schedulers and :func:`get_message_publisher`."""
    global _publisher
    if _publisher is None:
        with _lock:
            if _publisher is None:
                _publisher = create_message_publisher()
    return _publisher


def ensure_message_receiver() -> MessageReceiver:
    """Lazy singleton (sync); use from schedulers and :func:`get_message_receiver`."""
    global _receiver
    if _receiver is None:
        with _lock:
            if _receiver is None:
                _receiver = create_message_receiver()
    return _receiver


async def get_message_publisher() -> MessagePublisher:
    return ensure_message_publisher()


async def get_message_receiver() -> MessageReceiver:
    return ensure_message_receiver()
