from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OrganizationInvitationNotification:
    invitation_id: UUID
    organization_id: UUID
    organization_name: str
    email: str
    expires_at: datetime
    token: str
