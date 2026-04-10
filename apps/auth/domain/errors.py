class InvalidCredentialsError(Exception):
    """Raised when email/password do not match a stored user."""


class InvalidTokenError(Exception):
    """Raised when an access token is missing, malformed, or fails verification."""
