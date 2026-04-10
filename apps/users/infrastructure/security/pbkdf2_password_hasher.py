import hashlib
import hmac
import secrets
from typing import Final

from apps.users.domain.ports.password_hasher import PasswordHasher

_ITERATIONS: Final[int] = 390_000


class Pbkdf2PasswordHasher(PasswordHasher):
    """Stdlib PBKDF2-HMAC-SHA256 hasher (suitable for app wiring; tune for production)."""

    def hash(self, plain_password: str) -> str:
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            _ITERATIONS,
        )
        return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${dk.hex()}"

    def verify(self, plain_password: str, stored_hash: str) -> bool:
        try:
            _, iters_s, salt_hex, hash_hex = stored_hash.split("$", 3)
            iterations = int(iters_s)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
        except (ValueError, IndexError):
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(dk, expected)
