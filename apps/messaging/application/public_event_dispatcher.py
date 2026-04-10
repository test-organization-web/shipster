"""Wire :class:`~apps.shared.domain.ports.public_events.PublicEventDispatcher` to the broker."""

import json
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import date
from typing import Any
from uuid import UUID

from apps.messaging.domain.ports.messaging import MessagePublisher
from apps.shared.domain.event import Event


def _jsonify(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonify(v) for v in value]
    return value


def _payload_to_plain(payload: Any) -> Any:
    if is_dataclass(payload) and not isinstance(payload, type):
        return asdict(payload)
    model_dump = getattr(payload, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    raise TypeError(f"Unsupported event payload type: {type(payload)!r}")


class MessagePublisherPublicEventDispatcher:
    """Publishes :class:`~apps.shared.domain.event.Event` envelopes to the broker."""

    def __init__(self, publisher: MessagePublisher) -> None:
        self._publisher = publisher

    async def dispatch(self, event: Event[Any]) -> None:
        envelope = {
            "topic": event.topic,
            "subject": event.subject,
            "delivery_count": event.delivery_count,
            "payload": _jsonify(_payload_to_plain(event.payload)),
        }
        body = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
        event_key = event.topic.rsplit(".", maxsplit=1)[-1]
        await self._publisher.publish(
            event.topic,
            body,
            headers={"event": event_key, "subject": event.subject},
        )
