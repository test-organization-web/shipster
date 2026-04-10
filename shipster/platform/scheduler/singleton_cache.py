"""Lazy singletons for scheduled jobs (e.g. one stream processor per process)."""

import threading
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

_lock = threading.Lock()
_instances: dict[str, object] = {}


def get_or_create_singleton(job_key: str, factory: Callable[[], T]) -> T:
    """Return a cached instance keyed by ``job_key`` (double-checked locking)."""
    cached = _instances.get(job_key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    with _lock:
        if job_key not in _instances:
            _instances[job_key] = factory()
        return _instances[job_key]  # type: ignore[return-value]
