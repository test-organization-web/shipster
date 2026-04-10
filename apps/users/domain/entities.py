from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class User:
    """Internal user aggregate root."""

    id: UUID
    email: str
    username: str
    password_hash: str
