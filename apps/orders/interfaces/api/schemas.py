from uuid import UUID

from pydantic import BaseModel, Field


class CreateOrderRequest(BaseModel):
    order_number: str = Field(..., min_length=1, max_length=64)
    user_id: UUID | None = None


class OrderResponse(BaseModel):
    id: UUID
    order_number: str
    user_id: UUID | None
