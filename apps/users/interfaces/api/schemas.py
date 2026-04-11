from uuid import UUID

from pydantic import BaseModel, Field


class UserOrganizationResponse(BaseModel):
    organization_id: UUID
    organization_name: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    organizations: list[UserOrganizationResponse] = Field(default_factory=list)
