from uuid import UUID

from apps.orders.domain.entities import Order
from apps.orders.domain.errors import OrderNotFoundError
from apps.orders.domain.ports.order_repository import OrderRepository


class GetOrderById:
    """Load an order by id."""

    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    async def execute(self, order_id: UUID) -> Order:
        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(str(order_id))
        return order
