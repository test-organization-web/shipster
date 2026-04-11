import secrets
from uuid import UUID

from apps.users.domain.entities import User
from apps.users.domain.ports.password_hasher import PasswordHasher
from apps.users.domain.ports.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from apps.users.domain.ports.user_repository import UserRepository


class UserSubjectDataEraser:
    """Anonymize core user PII and rotate password to an unusable hash."""

    def __init__(
        self,
        *,
        users: UserRepository,
        password_reset_tokens: PasswordResetTokenRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._users = users
        self._password_reset_tokens = password_reset_tokens
        self._password_hasher = password_hasher

    async def erase_for_user(self, user_id: UUID) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            return
        await self._password_reset_tokens.delete_all_for_user(user_id)
        new_email = f"erased+{user.id.hex}@invalid.shipster"
        new_username = f"e{user.id.hex[:31]}"
        new_password_hash = self._password_hasher.hash(secrets.token_hex(32))
        await self._users.save(
            User(
                id=user.id,
                email=new_email,
                username=new_username,
                password_hash=new_password_hash,
            ),
        )
