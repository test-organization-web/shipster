from typing import Protocol
from uuid import UUID

from apps.orders.domain.entities import Order


class OrderRepository(Protocol):
    async def get_by_id(self, order_id: UUID) -> Order | None:
        """Return order by primary key."""

    async def count_by_user_id(self, user_id: UUID) -> int:
        """Return how many orders belong to the user."""

    async def list_by_user_id(self, user_id: UUID) -> list[Order]:
        """Return all orders owned by the user."""

    async def get_by_order_number(self, order_number: str) -> Order | None:
        """Return order by normalized order number."""

    async def save(self, order: Order) -> None:
        """Persist new or updated order."""
