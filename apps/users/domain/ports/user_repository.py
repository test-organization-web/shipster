from typing import Protocol
from uuid import UUID

from apps.users.domain.entities import User


class UserRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return user by primary key."""

    async def get_by_email(self, email: str) -> User | None:
        """Return user by normalized email."""

    async def get_by_username(self, username: str) -> User | None:
        """Return user by normalized username (lowercase)."""

    async def save(self, user: User) -> None:
        """Persist new or updated user."""
