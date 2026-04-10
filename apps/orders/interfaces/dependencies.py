from fastapi import Depends

from apps.orders.application.create_order import CreateOrder
from apps.orders.application.get_order import GetOrderById
from shipster.platform.persistence import ShipsterUnitOfWork, get_uow


async def get_create_order(
    uow: ShipsterUnitOfWork = Depends(get_uow),
) -> CreateOrder:
    return CreateOrder(orders=uow.orders)


async def get_get_order_by_id(
    uow: ShipsterUnitOfWork = Depends(get_uow),
) -> GetOrderById:
    return GetOrderById(orders=uow.orders)
