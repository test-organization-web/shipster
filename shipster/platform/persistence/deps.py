"""FastAPI dependencies for global DB session and unit of work."""

from collections.abc import AsyncIterator

import redis.asyncio as redis_async
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shipster.platform.persistence.database import get_async_session_factory
from shipster.platform.persistence.uow import ShipsterUnitOfWork
from shipster.platform.redis_client import get_async_redis


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_async_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_uow(session: AsyncSession = Depends(get_session)) -> ShipsterUnitOfWork:
    return ShipsterUnitOfWork(session)


async def get_redis() -> redis_async.Redis:
    return get_async_redis()
