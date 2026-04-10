"""Typed payloads and topic names for organization integration events."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

ORGANIZATION_INVITATION_CREATED_TOPIC = "public.organization_invitation_created"


@dataclass(frozen=True, slots=True)
class OrganizationInvitationCreatedPayload:
    invitation_id: UUID
    organization_id: UUID
    organization_name: str
    email: str
    invited_by_user_id: UUID | None
    expires_at: datetime
    token: str
