"""Redis Streams adapters for shared messaging ports (publish + consumer groups)."""

import base64
import json
from collections.abc import Mapping, Sequence

import redis.asyncio as redis_async
from redis.exceptions import ResponseError

from apps.messaging.domain.ports.messaging import ReceivedMessage


class RedisStreamMessaging:
    """Maps logical topics to stream keys ``{prefix}{topic}``; pull uses consumer groups."""

    def __init__(
        self,
        redis: redis_async.Redis,
        *,
        stream_key_prefix: str = "shipster:msg:",
    ) -> None:
        self._redis = redis
        self._stream_key_prefix = stream_key_prefix

    def _stream_key(self, topic: str) -> str:
        if not topic.strip():
            raise ValueError("topic must be non-empty")
        return f"{self._stream_key_prefix}{topic}"

    async def publish(
        self,
        topic: str,
        body: bytes,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        stream_key = self._stream_key(topic)
        fields: dict[str, str] = {
            "data_b64": base64.b64encode(body).decode("ascii"),
        }
        if headers:
            fields["headers_json"] = json.dumps(dict(headers), separators=(",", ":"))

        msg_id = await self._redis.xadd(stream_key, fields)
        if isinstance(msg_id, bytes):
            return msg_id.decode("utf-8")
        return str(msg_id)

    async def _ensure_consumer_group(self, stream_key: str, subscription: str) -> None:
        try:
            await self._redis.xgroup_create(
                name=stream_key,
                groupname=subscription,
                id="0",
                mkstream=True,
            )
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def pull(
        self,
        topic: str,
        *,
        subscription: str,
        consumer_id: str,
        max_messages: int = 10,
        block_ms: int | None = 5000,
    ) -> list[ReceivedMessage]:
        if not subscription.strip():
            raise ValueError("subscription must be non-empty")
        if not consumer_id.strip():
            raise ValueError("consumer_id must be non-empty")
        if max_messages < 1:
            raise ValueError("max_messages must be >= 1")

        stream_key = self._stream_key(topic)
        await self._ensure_consumer_group(stream_key, subscription)

        raw = await self._redis.xreadgroup(
            groupname=subscription,
            consumername=consumer_id,
            streams={stream_key: ">"},
            count=max_messages,
            block=block_ms,
        )
        if not raw:
            return []

        out: list[ReceivedMessage] = []
        for _stream_name, entries in raw:
            for msg_id, field_map in entries:
                out.append(self._decode_entry(msg_id, field_map))
        return out

    def _decode_entry(self, msg_id: str | bytes, field_map: Mapping) -> ReceivedMessage:
        if isinstance(msg_id, bytes):
            msg_id_s = msg_id.decode("utf-8")
        else:
            msg_id_s = str(msg_id)

        data_b64 = field_map.get("data_b64") or field_map.get(b"data_b64")
        if data_b64 is None:
            raise ValueError("stream entry missing data_b64 field")

        if isinstance(data_b64, bytes):
            data_b64_s = data_b64.decode("ascii")
        else:
            data_b64_s = str(data_b64)

        body = base64.b64decode(data_b64_s, validate=True)

        headers: dict[str, str] = {}
        raw_headers = field_map.get("headers_json") or field_map.get(b"headers_json")
        if raw_headers:
            if isinstance(raw_headers, bytes):
                raw_headers = raw_headers.decode("utf-8")
            parsed = json.loads(raw_headers)
            if not isinstance(parsed, dict):
                raise ValueError("headers_json must be a JSON object")
            headers = {str(k): str(v) for k, v in parsed.items()}

        return ReceivedMessage(id=msg_id_s, body=body, headers=headers)

    async def acknowledge(
        self,
        topic: str,
        *,
        subscription: str,
        message_ids: Sequence[str],
    ) -> None:
        if not subscription.strip():
            raise ValueError("subscription must be non-empty")
        if not message_ids:
            return

        stream_key = self._stream_key(topic)
        ids = list(message_ids)
        await self._redis.xack(stream_key, subscription, *ids)
