from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str


class CreateOrganizationBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=64)


class OrganizationMemberResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID


class InviteOrganizationMemberBody(BaseModel):
    email: EmailStr


class InvitationCreatedResponse(BaseModel):
    invitation_id: UUID
    email: str
    expires_at: datetime
    token: str = Field(
        ...,
        description="Secret value to share with the invitee; shown only once.",
    )


class AcceptOrganizationInvitationBody(BaseModel):
    token: str = Field(..., min_length=1)
