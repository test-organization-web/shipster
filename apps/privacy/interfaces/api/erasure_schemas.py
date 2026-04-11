from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ErasureRequestAcceptedResponse(BaseModel):
    request_id: UUID
    status: str


class ErasureStatusResponse(BaseModel):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    failure_reason: str | None
