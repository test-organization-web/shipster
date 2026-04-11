from uuid import UUID

from apps.orders.domain.ports.order_data_exporter import OrderDataExporter
from apps.orders.domain.ports.order_repository import OrderRepository
from apps.users.domain.errors import UserNotFoundError
from apps.users.domain.ports.user_repository import UserRepository


class RepositoryOrderDataExporter(OrderDataExporter):
    def __init__(self, *, orders: OrderRepository, users: UserRepository) -> None:
        self._orders = orders
        self._users = users

    async def export_for_user(self, user_id: UUID) -> dict[str, object]:
        if await self._users.get_by_id(user_id) is None:
            raise UserNotFoundError(str(user_id))
        orders = await self._orders.list_by_user_id(user_id)
        return {
            "orders": [
                {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "user_id": None if order.user_id is None else str(order.user_id),
                }
                for order in orders
            ]
        }
