"""Global unit of work: one SQLAlchemy session, repositories for all bounded contexts."""

from sqlalchemy.ext.asyncio import AsyncSession

from apps.orders.domain.ports.order_repository import OrderRepository
from apps.orders.infrastructure.persistence.repository.order import SqlAlchemyOrderRepository
from apps.organizations.domain.ports.organization_invitation_repository import (
    OrganizationInvitationRepository,
)
from apps.organizations.domain.ports.organization_member_repository import (
    OrganizationMemberRepository,
)
from apps.organizations.domain.ports.organization_repository import OrganizationRepository
from apps.organizations.infrastructure.persistence.repository.organization import (
    SqlAlchemyOrganizationRepository,
)
from apps.organizations.infrastructure.persistence.repository.organization_invitation import (
    SqlAlchemyOrganizationInvitationRepository,
)
from apps.organizations.infrastructure.persistence.repository.organization_member import (
    SqlAlchemyOrganizationMemberRepository,
)
from apps.users.domain.ports.user_repository import UserRepository
from apps.users.infrastructure.persistence.repository.user import (
    SqlAlchemyUserRepository,
)


class ShipsterUnitOfWork:
    """Request-scoped UoW; add aggregates here as new apps are wired in."""

    __slots__ = (
        "_orders",
        "_organization_invitations",
        "_organization_members",
        "_organizations",
        "_users",
    )

    def __init__(self, session: AsyncSession) -> None:
        self._users = SqlAlchemyUserRepository(session)
        self._orders = SqlAlchemyOrderRepository(session)
        self._organizations = SqlAlchemyOrganizationRepository(session)
        self._organization_members = SqlAlchemyOrganizationMemberRepository(session)
        self._organization_invitations = SqlAlchemyOrganizationInvitationRepository(session)

    @property
    def users(self) -> UserRepository:
        return self._users

    @property
    def orders(self) -> OrderRepository:
        return self._orders

    @property
    def organizations(self) -> OrganizationRepository:
        return self._organizations

    @property
    def organization_members(self) -> OrganizationMemberRepository:
        return self._organization_members

    @property
    def organization_invitations(self) -> OrganizationInvitationRepository:
        return self._organization_invitations
