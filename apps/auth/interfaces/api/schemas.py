import re

from pydantic import BaseModel, EmailStr, Field, field_validator

_USERNAME_RE = re.compile(r"^[a-z0-9_-]{3,32}$")


class RegisterBody(BaseModel):
    email: EmailStr
    username: str = Field(
        min_length=1,
        max_length=32,
        description="Unique handle; normalized to lowercase. Allowed: letters, digits, _, -",
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="At least 8 characters",
    )

    @field_validator("username")
    @classmethod
    def normalize_and_validate_username(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _USERNAME_RE.fullmatch(normalized):
            msg = (
                "Username must be 3–32 characters and contain only lowercase letters, "
                "digits, underscore, or hyphen (after trimming)."
            )
            raise ValueError(msg)
        return normalized


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
