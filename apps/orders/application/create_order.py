from uuid import UUID, uuid4

from apps.orders.domain.entities import Order
from apps.orders.domain.errors import OrderNumberAlreadyUsedError
from apps.orders.domain.ports.order_repository import OrderRepository


class CreateOrder:
    """Create a new order with a unique order number."""

    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    async def execute(self, *, order_number: str, user_id: UUID | None = None) -> Order:
        normalized = order_number.strip()
        if await self._orders.get_by_order_number(normalized) is not None:
            raise OrderNumberAlreadyUsedError(normalized)
        order = Order(id=uuid4(), order_number=normalized, user_id=user_id)
        await self._orders.save(order)
        return order
