"""Process-wide Redis clients (sync legacy + asyncio for messaging)."""

import redis.asyncio as redis_async
from redis import Redis

from shipster.platform.settings import get_global_settings

_redis: Redis | None = None
_async_redis: redis_async.Redis | None = None


def _redis_url() -> str:
    return get_global_settings().redis_url


def get_async_redis() -> redis_async.Redis:
    """Return a shared :class:`redis.asyncio.Redis` client (lazy singleton)."""
    global _async_redis
    if _async_redis is None:
        _async_redis = redis_async.from_url(_redis_url(), decode_responses=True)
    return _async_redis


async def close_async_redis() -> None:
    """Close pooled async connections (call from async app shutdown)."""
    global _async_redis
    if _async_redis is not None:
        await _async_redis.aclose()
        _async_redis = None
