from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, plain_password: str) -> str:
        """Produce a stored password representation (e.g. salted hash)."""

    def verify(self, plain_password: str, stored_hash: str) -> bool:
        """Check a plaintext password against stored hash."""
