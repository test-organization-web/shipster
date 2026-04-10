"""Parameters for :meth:`~apps.messaging.domain.ports.messaging.MessageReceiver.pull`."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StreamConsumerParams:
    """Subscription / consumer group name and consumer id for stream-style receivers."""

    subscription: str
    consumer_id: str
    max_messages: int = 10
    block_ms: int | None = 500
