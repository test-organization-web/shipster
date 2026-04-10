from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Order:
    """Internal order aggregate root (canonical model)."""

    id: UUID
    order_number: str
    user_id: UUID | None
