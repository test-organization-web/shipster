from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.domain.entities import User
from apps.users.domain.ports.user_repository import UserRepository
from apps.users.infrastructure.persistence.mappers import user_domain_to_row, user_row_to_domain
from apps.users.infrastructure.persistence.schema.user import UserORM


class SqlAlchemyUserRepository(UserRepository):
    """PostgreSQL/SQLite-backed repository; inject a scoped ``AsyncSession`` per unit of work."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserORM, user_id)
        return None if row is None else user_row_to_domain(row)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserORM).where(UserORM.email == email).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return None if row is None else user_row_to_domain(row)

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(UserORM).where(UserORM.username == username).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return None if row is None else user_row_to_domain(row)

    async def save(self, user: User) -> None:
        existing = await self._session.get(UserORM, user.id)
        if existing is None:
            self._session.add(user_domain_to_row(user))
            return
        existing.email = user.email
        existing.username = user.username
        existing.password_hash = user.password_hash
