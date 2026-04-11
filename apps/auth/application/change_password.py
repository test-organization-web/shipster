from uuid import UUID

from apps.users.domain.entities import User
from apps.users.domain.errors import InvalidCurrentPasswordError, UserNotFoundError
from apps.users.domain.ports.password_hasher import PasswordHasher
from apps.users.domain.ports.user_repository import UserRepository


class ChangePassword:
    """Replace password after verifying the current one."""

    def __init__(self, users: UserRepository, password_hasher: PasswordHasher) -> None:
        self._users = users
        self._password_hasher = password_hasher

    async def execute(self, *, user_id: UUID, current_password: str, new_password: str) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        if not self._password_hasher.verify(current_password, user.password_hash):
            raise InvalidCurrentPasswordError()
        updated = User(
            id=user.id,
            email=user.email,
            username=user.username,
            password_hash=self._password_hasher.hash(new_password),
        )
        await self._users.save(updated)
