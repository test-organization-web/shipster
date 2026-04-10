from typing import Protocol
from uuid import UUID


class AccessTokenService(Protocol):
    """Issue and verify signed access tokens for authenticated subjects (e.g. JWT)."""

    def issue(self, user_id: UUID) -> str:
        """Return a new access token for the given user id."""

    def verify(self, token: str) -> UUID:
        """Parse and validate a token; return the subject user id or raise ``InvalidTokenError``."""
