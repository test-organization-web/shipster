import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from apps.users.domain.ports.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from apps.users.domain.ports.user_repository import UserRepository

_TOKEN_BYTES = 32
_DEFAULT_RESET_HOURS = 24


def _hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class RequestPasswordReset:
    """If the email is registered, revoke prior active tokens and store a new pending token.

    A scheduler sends the email and marks the row NOTIFIED
    (see ``ProcessPasswordResetNotifications``).
    """

    def __init__(
        self,
        users: UserRepository,
        reset_tokens: PasswordResetTokenRepository,
        *,
        token_ttl_hours: int = _DEFAULT_RESET_HOURS,
    ) -> None:
        self._users = users
        self._reset_tokens = reset_tokens
        self._token_ttl_hours = token_ttl_hours

    async def execute(self, *, email: str) -> None:
        normalized = email.strip().lower()
        user = await self._users.get_by_email(normalized)
        if user is None:
            return
        await self._reset_tokens.revoke_active_for_user(user.id)
        raw_token = secrets.token_urlsafe(_TOKEN_BYTES)
        expires_at = datetime.now(UTC) + timedelta(hours=self._token_ttl_hours)
        await self._reset_tokens.save(
            user_id=user.id,
            token_hash=_hash_reset_token(raw_token),
            expires_at=expires_at,
            pending_plain_token=raw_token,
        )
