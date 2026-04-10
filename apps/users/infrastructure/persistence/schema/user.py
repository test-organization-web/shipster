from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from apps.users.infrastructure.persistence.base import Base


class UserORM(Base):
    """Database row for `users` (not the domain entity)."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(1024), nullable=False)
