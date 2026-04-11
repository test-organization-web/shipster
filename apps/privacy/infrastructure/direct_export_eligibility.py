import logging
from uuid import UUID

from apps.orders.domain.ports.order_repository import OrderRepository
from apps.organizations.domain.ports.organization_invitation_repository import (
    OrganizationInvitationRepository,
)
from apps.organizations.domain.ports.organization_member_repository import (
    OrganizationMemberRepository,
)
from apps.users.domain.errors import UserNotFoundError
from apps.users.domain.ports.user_repository import UserRepository

_BASE_EXPORT_BYTES = 512
_MEMBERSHIP_EXPORT_BYTES = 160
_INVITATION_EXPORT_BYTES = 320
_ORDER_EXPORT_BYTES = 160

_LOG = logging.getLogger(__name__)


class RepositoryDirectExportEligibilityProbe:
    def __init__(
        self,
        *,
        users: UserRepository,
        members: OrganizationMemberRepository,
        invitations: OrganizationInvitationRepository,
        orders: OrderRepository,
        direct_export_max_bytes: int,
    ) -> None:
        self._users = users
        self._members = members
        self._invitations = invitations
        self._orders = orders
        self._direct_export_max_bytes = direct_export_max_bytes

    async def is_direct_export_eligible(self, subject_user_id: UUID) -> bool:
        user = await self._users.get_by_id(subject_user_id)
        if user is None:
            raise UserNotFoundError(str(subject_user_id))

        membership_count = await self._members.count_by_user(subject_user_id)
        invitation_count = await self._invitations.count_by_email(user.email)
        order_count = await self._orders.count_by_user_id(subject_user_id)

        estimated_bytes = (
            _BASE_EXPORT_BYTES
            + len(user.email)
            + len(user.username)
            + membership_count * _MEMBERSHIP_EXPORT_BYTES
            + invitation_count * _INVITATION_EXPORT_BYTES
            + order_count * _ORDER_EXPORT_BYTES
        )
        eligible = estimated_bytes <= self._direct_export_max_bytes
        _LOG.debug(
            "privacy export: direct eligibility computed",
            extra={
                "subject_user_id": str(subject_user_id),
                "eligible": eligible,
                "estimated_bytes": estimated_bytes,
                "direct_export_max_bytes": self._direct_export_max_bytes,
            },
        )
        return eligible
