from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class Organization:
    """Internal organization aggregate root."""

    id: UUID
    name: str
    slug: str


@dataclass(frozen=True, slots=True)
class OrganizationMember:
    """Membership of a user in an organization."""

    id: UUID
    organization_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class OrganizationInvitation:
    """Pending or finalized invitation to join an organization by email."""

    id: UUID
    organization_id: UUID
    email: str
    token_hash: str
    invited_by_user_id: UUID | None
    created_at: datetime
    expires_at: datetime
    status: InvitationStatus
    accepted_at: datetime | None
