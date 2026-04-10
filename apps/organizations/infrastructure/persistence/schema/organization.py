from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from apps.users.infrastructure.persistence.base import Base


class OrganizationORM(Base):
    """Database row for ``organizations`` (not the domain entity)."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
