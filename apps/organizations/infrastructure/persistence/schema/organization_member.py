from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from apps.users.infrastructure.persistence.base import Base


class OrganizationMemberORM(Base):
    """Database row for ``organization_members`` (not the domain entity)."""

    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_member_org_user",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
