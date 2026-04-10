from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ReceivedMessage:
    """Inbound message with broker id (delivery semantics depend on the backend)."""

    id: str
    body: bytes
    headers: Mapping[str, str]


class MessagePublisher(Protocol):
    """Publish messages to a logical topic; backend maps topics to streams/queues/exchanges."""

    async def publish(
        self,
        topic: str,
        body: bytes,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        """Publish a payload; returns a broker-specific message identifier."""


class MessageReceiver(Protocol):
    """Pull and acknowledge messages; ``subscription`` maps to consumer group / queue name."""

    async def pull(
        self,
        topic: str,
        *,
        subscription: str,
        consumer_id: str,
        max_messages: int = 10,
        block_ms: int | None = 5000,
    ) -> list[ReceivedMessage]:
        """Return newly delivered messages (e.g. Redis ``>``), blocking up to ``block_ms``."""

    async def acknowledge(
        self,
        topic: str,
        *,
        subscription: str,
        message_ids: Sequence[str],
    ) -> None:
        """Confirm processing so the broker does not redeliver (best-effort per backend)."""
