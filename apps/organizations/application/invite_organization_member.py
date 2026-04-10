import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID, uuid4

from apps.organizations.domain.entities import InvitationStatus, OrganizationInvitation
from apps.organizations.domain.errors import (
    MemberAlreadyExistsError,
    NotOrganizationMemberError,
    OrganizationNotFoundError,
    PendingInvitationExistsError,
)
from apps.organizations.domain.organization_public_events import (
    ORGANIZATION_INVITATION_CREATED_TOPIC,
    OrganizationInvitationCreatedPayload,
)
from apps.organizations.domain.ports.organization_invitation_repository import (
    OrganizationInvitationRepository,
)
from apps.organizations.domain.ports.organization_member_repository import (
    OrganizationMemberRepository,
)
from apps.organizations.domain.ports.organization_repository import OrganizationRepository
from apps.shared.domain.event import Event
from apps.shared.domain.ports.public_events import PublicEventDispatcher
from apps.users.domain.ports.user_repository import UserRepository

_LOG = logging.getLogger(__name__)
# Must match REQUEST_TIMING_LOGGER in shipster.platform.logging_bootstrap.
_PERF_LOG = logging.getLogger("shipster.debug.request_timing")

_TOKEN_BYTES = 32
_DEFAULT_INVITATION_DAYS = 7


def _hash_invitation_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def organization_invitation_created_payload(
    invitation: OrganizationInvitation,
    raw_token: str,
    organization_name: str,
) -> OrganizationInvitationCreatedPayload:
    """Typed payload for broker publish and downstream consumers."""
    return OrganizationInvitationCreatedPayload(
        invitation_id=invitation.id,
        organization_id=invitation.organization_id,
        organization_name=organization_name,
        email=invitation.email,
        invited_by_user_id=invitation.invited_by_user_id,
        expires_at=invitation.expires_at,
        token=raw_token,
    )


async def dispatch_organization_invitation_created(
    public_events: PublicEventDispatcher,
    invitation: OrganizationInvitation,
    raw_token: str,
    organization_name: str,
) -> None:
    """Publish invitation-created through the public event dispatcher (broker)."""
    t0 = perf_counter()
    try:
        await public_events.dispatch(
            Event(
                topic=ORGANIZATION_INVITATION_CREATED_TOPIC,
                subject=str(invitation.id),
                payload=organization_invitation_created_payload(
                    invitation,
                    raw_token,
                    organization_name,
                ),
                delivery_count=0,
            ),
        )
    except Exception:
        _LOG.exception(
            "Failed to publish organization invitation created event",
            extra={
                "event": "organization_invitation_publish_failed",
                "invitation_id": invitation.id,
                "organization_id": invitation.organization_id,
            },
        )
    else:
        _PERF_LOG.debug(
            "invite_member broker_publish_s=%.4f invitation_id=%s",
            perf_counter() - t0,
            invitation.id,
        )


@dataclass(frozen=True, slots=True)
class InviteOrganizationMemberResult:
    invitation: OrganizationInvitation
    raw_token: str


class InviteOrganizationMember:
    """Create a pending invitation; only existing org members may invite."""

    def __init__(
        self,
        organizations: OrganizationRepository,
        users: UserRepository,
        members: OrganizationMemberRepository,
        invitations: OrganizationInvitationRepository,
        public_events: PublicEventDispatcher,
    ) -> None:
        self._organizations = organizations
        self._users = users
        self._members = members
        self._invitations = invitations
        self._public_events = public_events

    async def execute(
        self,
        *,
        organization_id: UUID,
        email: str,
        invited_by_user_id: UUID,
    ) -> InviteOrganizationMemberResult:
        t0 = perf_counter()
        organization = await self._organizations.get_by_id(organization_id)
        if organization is None:
            raise OrganizationNotFoundError(str(organization_id))
        if (
            await self._members.find_by_organization_and_user(organization_id, invited_by_user_id)
            is None
        ):
            raise NotOrganizationMemberError()

        normalized_email = email.strip().lower()
        if (
            await self._invitations.find_pending_by_organization_and_email(
                organization_id,
                normalized_email,
            )
            is not None
        ):
            raise PendingInvitationExistsError()

        existing_user = await self._users.get_by_email(normalized_email)
        if existing_user is not None:
            if (
                await self._members.find_by_organization_and_user(
                    organization_id,
                    existing_user.id,
                )
                is not None
            ):
                raise MemberAlreadyExistsError()

        raw_token = secrets.token_urlsafe(_TOKEN_BYTES)
        token_hash = _hash_invitation_token(raw_token)
        now = datetime.now(UTC)
        invitation = OrganizationInvitation(
            id=uuid4(),
            organization_id=organization_id,
            email=normalized_email,
            token_hash=token_hash,
            invited_by_user_id=invited_by_user_id,
            created_at=now,
            expires_at=now + timedelta(days=_DEFAULT_INVITATION_DAYS),
            status=InvitationStatus.PENDING,
            accepted_at=None,
        )
        t_after_queries = perf_counter()
        await self._invitations.save(invitation)
        await dispatch_organization_invitation_created(
            self._public_events,
            invitation,
            raw_token,
            organization.name,
        )
        t_end = perf_counter()
        _LOG.info(
            "Organization invitation created",
            extra={
                "event": "organization_invitation_created",
                "invitation_id": invitation.id,
                "organization_id": invitation.organization_id,
                "organization_name": organization.name,
                "invited_by_user_id": invitation.invited_by_user_id,
                "expires_at": invitation.expires_at,
            },
        )
        _PERF_LOG.debug(
            "invite_member use_case organization_id=%s queries_s=%.4f save_s=%.4f total_s=%.4f",
            organization_id,
            t_after_queries - t0,
            t_end - t_after_queries,
            t_end - t0,
        )
        return InviteOrganizationMemberResult(invitation=invitation, raw_token=raw_token)
