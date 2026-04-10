from typing import Protocol

from apps.users.domain.ports.user_repository import UserRepository


class UnitOfWork(Protocol):
    """Transaction boundary: repositories participating in the same commit share one UoW."""

    @property
    async def users(self) -> UserRepository:
        """User aggregate repository for this unit of work."""
