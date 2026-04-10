"""RabbitMQ adapter: topic exchange and queues bound to the message ``topic`` routing key."""

import asyncio
import contextlib
import time
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

import aio_pika

from apps.messaging.domain.ports.messaging import ReceivedMessage


def _sanitize_segment(value: str, *, max_len: int = 80) -> str:
    cleaned = "".join(c if c.isalnum() or c in "._-" else "_" for c in value.strip())
    return cleaned[:max_len] or "empty"


class RabbitMqMessaging:
    """Async RabbitMQ adapter built on top of ``aio-pika``."""

    def __init__(self, url: str, *, exchange_name: str = "shipster.msg") -> None:
        if not url.strip():
            raise ValueError("RabbitMQ URL must be non-empty")
        self._url = url
        self._exchange_name = exchange_name
        self._topology_lock = asyncio.Lock()
        self._pending_lock = asyncio.Lock()
        self._connection: Any = None
        self._publish_channel: Any = None
        self._publish_exchange: Any = None
        self._consume_channel: Any = None
        self._consume_exchange: Any = None
        self._consume_queues: dict[tuple[str, str], Any] = {}
        self._pending_messages: dict[str, Any] = {}

    @staticmethod
    def _is_closed(resource: Any) -> bool:
        return resource is None or bool(getattr(resource, "is_closed", False))

    async def _ensure_connection(self) -> Any:
        if self._is_closed(self._connection):
            self._connection = await aio_pika.connect_robust(self._url)
            self._publish_channel = None
            self._publish_exchange = None
            self._consume_channel = None
            self._consume_exchange = None
            self._consume_queues = {}
            self._pending_messages = {}
        return self._connection

    async def _ensure_publish_exchange(self) -> Any:
        async with self._topology_lock:
            connection = await self._ensure_connection()
            if self._is_closed(self._publish_channel) or self._publish_exchange is None:
                self._publish_channel = await connection.channel()
                self._publish_exchange = await self._publish_channel.declare_exchange(
                    self._exchange_name,
                    aio_pika.ExchangeType.TOPIC,
                    durable=True,
                )
            return self._publish_exchange

    async def _ensure_queue_and_bind(
        self,
        topic: str,
        subscription: str,
        *,
        prefetch_count: int,
    ) -> Any:
        queue_key = (topic, subscription)
        async with self._topology_lock:
            connection = await self._ensure_connection()
            if self._is_closed(self._consume_channel) or self._consume_exchange is None:
                self._consume_channel = await connection.channel()
                self._consume_exchange = await self._consume_channel.declare_exchange(
                    self._exchange_name,
                    aio_pika.ExchangeType.TOPIC,
                    durable=True,
                )
                self._consume_queues = {}

            await self._consume_channel.set_qos(prefetch_count=prefetch_count)

            queue = self._consume_queues.get(queue_key)
            if queue is None:
                queue = await self._consume_channel.declare_queue(
                    self._queue_name(topic, subscription),
                    durable=True,
                    auto_delete=False,
                )
                await queue.bind(self._consume_exchange, routing_key=topic)
                self._consume_queues[queue_key] = queue
            return queue

    def _queue_name(self, topic: str, subscription: str) -> str:
        return f"shipster.q.{_sanitize_segment(subscription)}.{_sanitize_segment(topic)}"

    @staticmethod
    def _message_headers(message: Any) -> dict[str, str]:
        headers = getattr(message, "headers", None) or {}
        return {str(k): str(v) for k, v in headers.items()}

    @staticmethod
    def _message_id(message: Any) -> str:
        message_id = getattr(message, "message_id", None)
        if message_id is not None and str(message_id).strip():
            return str(message_id)
        delivery_tag = getattr(message, "delivery_tag", None)
        if delivery_tag is not None:
            return str(delivery_tag)
        return str(uuid.uuid4())

    async def publish(
        self,
        topic: str,
        body: bytes,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        if not topic.strip():
            raise ValueError("topic must be non-empty")

        exchange = await self._ensure_publish_exchange()
        msg_id = str(uuid.uuid4())
        message = aio_pika.Message(
            body=body,
            message_id=msg_id,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/octet-stream",
            headers=dict(headers) if headers else None,
        )
        await exchange.publish(
            message,
            routing_key=topic,
            mandatory=False,
        )
        return msg_id

    async def pull(
        self,
        topic: str,
        *,
        subscription: str,
        consumer_id: str,
        max_messages: int = 10,
        block_ms: int | None = 5000,
    ) -> list[ReceivedMessage]:
        del consumer_id

        if not topic.strip():
            raise ValueError("topic must be non-empty")
        if not subscription.strip():
            raise ValueError("subscription must be non-empty")
        if max_messages < 1:
            raise ValueError("max_messages must be >= 1")

        queue = await self._ensure_queue_and_bind(
            topic,
            subscription,
            prefetch_count=max_messages,
        )
        deadline = time.monotonic() + (block_ms / 1000.0) if block_ms is not None else None
        out: list[ReceivedMessage] = []

        while len(out) < max_messages:
            incoming = await queue.get(no_ack=False, fail=False)
            if incoming is None:
                if block_ms is None or (deadline is not None and time.monotonic() >= deadline):
                    break
                await asyncio.sleep(0.05)
                continue

            message_id = self._message_id(incoming)
            async with self._pending_lock:
                self._pending_messages[message_id] = incoming
            out.append(
                ReceivedMessage(
                    id=message_id,
                    body=incoming.body,
                    headers=self._message_headers(incoming),
                ),
            )

        return out

    async def acknowledge(
        self,
        topic: str,
        *,
        subscription: str,
        message_ids: Sequence[str],
    ) -> None:
        del topic, subscription

        if not message_ids:
            return

        to_ack: list[Any] = []
        async with self._pending_lock:
            for message_id in message_ids:
                message = self._pending_messages.pop(message_id, None)
                if message is not None:
                    to_ack.append(message)

        for message in to_ack:
            with contextlib.suppress(aio_pika.exceptions.MessageProcessError):
                await message.ack()
