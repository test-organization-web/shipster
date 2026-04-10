from uuid import UUID

from apps.auth.domain.ports.access_token import AccessTokenService


class VerifyAccessToken:
    """Parse a bearer token and return the authenticated user id."""

    def __init__(self, tokens: AccessTokenService) -> None:
        self._tokens = tokens

    def execute(self, token: str) -> UUID:
        return self._tokens.verify(token)
