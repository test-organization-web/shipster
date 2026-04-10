from uuid import UUID

from apps.users.domain.entities import User
from apps.users.domain.errors import UserNotFoundError
from apps.users.domain.ports.user_repository import UserRepository


class GetUserById:
    """Load a user by id."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(self, user_id: UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        return user
