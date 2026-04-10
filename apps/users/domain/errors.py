class UserNotFoundError(Exception):
    """Raised when a user cannot be loaded by identifier."""


class EmailAlreadyRegisteredError(Exception):
    """Raised when registration uses an email that already exists."""


class UsernameAlreadyTakenError(Exception):
    """Raised when registration uses a username that already exists."""
