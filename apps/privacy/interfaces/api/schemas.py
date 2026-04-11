from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ExportRequestAcceptedResponse(BaseModel):
    request_id: UUID
    status: str


class ExportStatusResponse(BaseModel):
    id: UUID
    status: str
    expires_at: datetime | None


class ExportLifecycleEventResponse(BaseModel):
    id: UUID
    type: str
    occurred_at: datetime
    actor_user_id: UUID | None = None


class ExportLifecycleEventsResponse(BaseModel):
    events: list[ExportLifecycleEventResponse]
    total: int
