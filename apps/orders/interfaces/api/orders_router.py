from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from apps.orders.application.create_order import CreateOrder
from apps.orders.application.get_order import GetOrderById
from apps.orders.domain.errors import OrderNotFoundError, OrderNumberAlreadyUsedError
from apps.orders.interfaces.api.schemas import CreateOrderRequest, OrderResponse
from apps.orders.interfaces.dependencies import get_create_order, get_get_order_by_id

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: CreateOrderRequest,
    use_case: CreateOrder = Depends(get_create_order),
) -> OrderResponse:
    try:
        order = await use_case.execute(order_number=body.order_number, user_id=body.user_id)
    except OrderNumberAlreadyUsedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order number already in use",
        ) from None
    return OrderResponse(id=order.id, order_number=order.order_number, user_id=order.user_id)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    use_case: GetOrderById = Depends(get_get_order_by_id),
) -> OrderResponse:
    try:
        order = await use_case.execute(order_id)
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        ) from None
    return OrderResponse(id=order.id, order_number=order.order_number, user_id=order.user_id)
