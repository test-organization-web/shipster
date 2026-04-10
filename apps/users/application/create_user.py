from uuid import uuid4

from apps.users.domain.entities import User
from apps.users.domain.errors import EmailAlreadyRegisteredError, UsernameAlreadyTakenError
from apps.users.domain.ports.password_hasher import PasswordHasher
from apps.users.domain.ports.user_repository import UserRepository


class CreateUser:
    """Register a new user with a unique email and username."""

    def __init__(self, users: UserRepository, password_hasher: PasswordHasher) -> None:
        self._users = users
        self._password_hasher = password_hasher

    async def execute(self, *, email: str, username: str, plain_password: str) -> User:
        normalized_email = email.strip().lower()
        normalized_username = username.strip().lower()
        if await self._users.get_by_email(normalized_email) is not None:
            raise EmailAlreadyRegisteredError(normalized_email)
        if await self._users.get_by_username(normalized_username) is not None:
            raise UsernameAlreadyTakenError(normalized_username)
        user = User(
            id=uuid4(),
            email=normalized_email,
            username=normalized_username,
            password_hash=self._password_hasher.hash(plain_password),
        )
        await self._users.save(user)
        return user
