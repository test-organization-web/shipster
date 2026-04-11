from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.orders.domain.entities import Order
from apps.orders.domain.ports.order_repository import OrderRepository
from apps.orders.infrastructure.persistence.mappers import order_domain_to_row, order_row_to_domain
from apps.orders.infrastructure.persistence.schema.order import OrderORM


class SqlAlchemyOrderRepository(OrderRepository):
    """SQLAlchemy-backed repository; inject a scoped ``AsyncSession`` per unit of work."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, order_id: UUID) -> Order | None:
        row = await self._session.get(OrderORM, order_id)
        return None if row is None else order_row_to_domain(row)

    async def count_by_user_id(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(OrderORM).where(OrderORM.user_id == user_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def list_by_user_id(self, user_id: UUID) -> list[Order]:
        stmt = select(OrderORM).where(OrderORM.user_id == user_id).order_by(OrderORM.id)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [order_row_to_domain(row) for row in rows]

    async def get_by_order_number(self, order_number: str) -> Order | None:
        stmt = select(OrderORM).where(OrderORM.order_number == order_number).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return None if row is None else order_row_to_domain(row)

    async def save(self, order: Order) -> None:
        existing = await self._session.get(OrderORM, order.id)
        if existing is None:
            self._session.add(order_domain_to_row(order))
            return
        existing.order_number = order.order_number
        existing.user_id = order.user_id
