"""Global persistence: engine, session factory, UoW, and HTTP dependencies."""

from shipster.platform.persistence.database import (
    get_async_engine,
    get_async_session_factory,
    get_engine,
    get_session_factory,
    init_async_database,
)
from shipster.platform.persistence.deps import get_redis, get_session, get_uow
from shipster.platform.persistence.uow import ShipsterUnitOfWork

__all__ = [
    "ShipsterUnitOfWork",
    "get_async_engine",
    "get_async_session_factory",
    "get_engine",
    "get_redis",
    "get_session",
    "get_session_factory",
    "get_uow",
    "init_async_database",
]
