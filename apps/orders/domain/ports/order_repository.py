from typing import Protocol
from uuid import UUID

from apps.orders.domain.entities import Order


class OrderRepository(Protocol):
    async def get_by_id(self, order_id: UUID) -> Order | None:
        """Return order by primary key."""

    async def get_by_order_number(self, order_number: str) -> Order | None:
        """Return order by normalized order number."""

    async def save(self, order: Order) -> None:
        """Persist new or updated order."""
