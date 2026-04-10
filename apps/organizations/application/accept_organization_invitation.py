import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from apps.organizations.domain.entities import InvitationStatus, OrganizationMember
from apps.organizations.domain.errors import (
    InvitationAlreadyUsedError,
    InvitationEmailMismatchError,
    InvitationExpiredError,
    InvitationNotFoundError,
)
from apps.organizations.domain.ports.organization_invitation_repository import (
    OrganizationInvitationRepository,
)
from apps.organizations.domain.ports.organization_member_repository import (
    OrganizationMemberRepository,
)
from apps.users.domain.errors import UserNotFoundError
from apps.users.domain.ports.user_repository import UserRepository


def _hash_invitation_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AcceptOrganizationInvitation:
    """Accept an invitation using the secret token; caller must be the invited email."""

    def __init__(
        self,
        users: UserRepository,
        members: OrganizationMemberRepository,
        invitations: OrganizationInvitationRepository,
    ) -> None:
        self._users = users
        self._members = members
        self._invitations = invitations

    async def execute(self, *, raw_token: str, accepting_user_id: UUID) -> OrganizationMember:
        token_hash = _hash_invitation_token(raw_token)
        invitation = await self._invitations.find_by_token_hash(token_hash)
        if invitation is None:
            raise InvitationNotFoundError()

        if invitation.status is not InvitationStatus.PENDING:
            raise InvitationAlreadyUsedError()

        now = datetime.now(UTC)
        if invitation.expires_at < now:
            raise InvitationExpiredError()

        user = await self._users.get_by_id(accepting_user_id)
        if user is None:
            raise UserNotFoundError(str(accepting_user_id))
        if user.email != invitation.email:
            raise InvitationEmailMismatchError()

        existing = await self._members.find_by_organization_and_user(
            invitation.organization_id,
            accepting_user_id,
        )
        if existing is not None:
            updated = replace(
                invitation,
                status=InvitationStatus.ACCEPTED,
                accepted_at=now,
            )
            await self._invitations.save(updated)
            return existing

        member = OrganizationMember(
            id=uuid4(),
            organization_id=invitation.organization_id,
            user_id=accepting_user_id,
        )
        await self._members.save(member)
        updated = replace(
            invitation,
            status=InvitationStatus.ACCEPTED,
            accepted_at=now,
        )
        await self._invitations.save(updated)
        return member
