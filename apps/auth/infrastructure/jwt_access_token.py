import hashlib
from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import UUID

import jwt

from apps.auth.domain.errors import InvalidTokenError

_DEFAULT_EXPIRES_MINUTES: Final[int] = 60
_MIN_HS256_KEY_BYTES: Final[int] = 32


def _hs256_key_material(secret: str) -> bytes:
    """Key bytes for HS256: RFC 7518 recommends >=32 bytes; PyJWT warns otherwise.

    Short secrets (e.g. legacy 29-char dev values) are stretched to 32 bytes via SHA-256
    so the same ``SHIPSTER_JWT_SECRET`` string still configures one stable key.
    Secrets that are already 32+ UTF-8 bytes are used verbatim (unchanged vs prior behavior).
    """
    raw = secret.encode("utf-8")
    if len(raw) >= _MIN_HS256_KEY_BYTES:
        return raw
    return hashlib.sha256(raw).digest()


class JwtAccessTokenService:
    """HS256 JWT implementation of ``AccessTokenService``."""

    def __init__(
        self,
        secret: str,
        *,
        algorithm: str = "HS256",
        expires_minutes: int = _DEFAULT_EXPIRES_MINUTES,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._expires_minutes = expires_minutes

    def issue(self, user_id: UUID) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=self._expires_minutes),
        }
        key = _hs256_key_material(self._secret)
        return jwt.encode(payload, key, algorithm=self._algorithm)

    def verify(self, token: str) -> UUID:
        try:
            key = _hs256_key_material(self._secret)
            payload = jwt.decode(
                token,
                key,
                algorithms=[self._algorithm],
            )
        except jwt.PyJWTError:
            raise InvalidTokenError() from None
        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise InvalidTokenError()
        try:
            return UUID(sub)
        except ValueError:
            raise InvalidTokenError() from None
