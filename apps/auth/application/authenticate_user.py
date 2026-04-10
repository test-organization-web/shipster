from apps.auth.domain.errors import InvalidCredentialsError
from apps.auth.domain.ports.access_token import AccessTokenService
from apps.users.domain.ports.password_hasher import PasswordHasher
from apps.users.domain.ports.user_repository import UserRepository


class AuthenticateUser:
    """Validate credentials and return an access token for the user."""

    def __init__(
        self,
        users: UserRepository,
        password_hasher: PasswordHasher,
        tokens: AccessTokenService,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._tokens = tokens

    async def execute(self, *, email: str, password: str) -> str:
        normalized = email.strip().lower()
        user = await self._users.get_by_email(normalized)
        if user is None or not self._password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError()
        return self._tokens.issue(user.id)
