from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from apps.users.infrastructure.persistence.base import Base


class OrderORM(Base):
    """Database row for ``orders`` (not the domain entity)."""

    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    order_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
