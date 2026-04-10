from apps.orders.domain.entities import Order
from apps.orders.infrastructure.persistence.schema.order import OrderORM


def order_row_to_domain(row: OrderORM) -> Order:
    return Order(id=row.id, order_number=row.order_number, user_id=row.user_id)


def order_domain_to_row(order: Order) -> OrderORM:
    return OrderORM(id=order.id, order_number=order.order_number, user_id=order.user_id)
