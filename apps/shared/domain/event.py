"""Generic public event envelope."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


def _serialize_payload_for_str(payload: Any) -> str:
    if is_dataclass(payload) and not isinstance(payload, type):
        return json.dumps(asdict(payload), default=str, separators=(",", ":"))
    model_dump_json = getattr(payload, "model_dump_json", None)
    if callable(model_dump_json):
        return model_dump_json()
    return repr(payload)


@dataclass(frozen=True, slots=True)
class Event(Generic[T]):
    topic: str
    subject: str
    payload: T
    delivery_count: int

    def __str__(self) -> str:
        p = _serialize_payload_for_str(self.payload)
        return (
            f"Event(topic={self.topic}, subject={self.subject}, "
            f"payload={p}, delivery_count={self.delivery_count})"
        )
