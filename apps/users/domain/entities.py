from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class UserPasswordResetTokenStatus(StrEnum):
    PENDING = "pending"
    NOTIFIED = "notified"
    REVOKED = "revoked"
    USED = "used"


@dataclass(frozen=True, slots=True)
class PasswordResetPendingNotification:
    """Row ready for outbound email (PENDING with a plaintext token not yet cleared)."""

    token_id: UUID
    user_id: UUID
    plain_token: str


@dataclass(frozen=True, slots=True)
class User:
    """Internal user aggregate root."""

    id: UUID
    email: str
    username: str
    password_hash: str
