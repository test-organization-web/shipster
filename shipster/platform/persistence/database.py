"""Process-wide SQLAlchemy async engine and session factory (shared by all apps)."""

from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from apps.users.infrastructure.persistence.base import Base
from shipster.platform.settings import get_global_settings


def _register_orm_metadata() -> None:
    """Import ORM models so ``Base.metadata`` is complete before ``create_all``."""
    from apps.orders.infrastructure.persistence.schema import OrderORM  # noqa: F401
    from apps.organizations.infrastructure.persistence.schema import (  # noqa: F401
        OrganizationInvitationORM,
        OrganizationMemberORM,
        OrganizationORM,
    )
    from apps.privacy.infrastructure.persistence.schema import (  # noqa: F401
        PrivacyErasureRequestORM,
        PrivacyExportLifecycleEventORM,
        PrivacyExportRequestORM,
    )
    from apps.users.infrastructure.persistence.schema import (  # noqa: F401
        UserORM,
        UserPasswordResetTokenORM,
    )


def _sqlite_connect_args(url: str) -> dict[str, bool]:
    return {"check_same_thread": False} if "sqlite" in url.lower() else {}


def _to_async_database_url(database_url: str) -> str:
    """Map sync URLs to async drivers (SQLite ``aiosqlite``, Postgres ``psycopg_async``)."""
    if "sqlite+pysqlite" in database_url:
        return database_url.replace("sqlite+pysqlite", "sqlite+aiosqlite", 1)
    if database_url.startswith("sqlite:///"):
        return "sqlite+aiosqlite:///" + database_url.removeprefix("sqlite:///")
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql+psycopg_async://", 1)
    msg = f"Unsupported database URL for async engine: {database_url!r}"
    raise ValueError(msg)


@lru_cache(maxsize=1)
def _create_async_engine(database_url: str) -> AsyncEngine:
    _register_orm_metadata()
    async_url = _to_async_database_url(database_url)
    return create_async_engine(async_url, connect_args=_sqlite_connect_args(database_url))


def get_async_engine(*, database_url: str | None = None) -> AsyncEngine:
    url = database_url if database_url is not None else get_global_settings().database_url
    return _create_async_engine(url)


@lru_cache(maxsize=1)
def get_async_session_factory():
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def init_async_database(*, database_url: str | None = None) -> None:
    """Create tables on the async engine (call once at application startup)."""
    engine = get_async_engine(database_url=database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
