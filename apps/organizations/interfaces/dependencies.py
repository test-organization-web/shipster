from fastapi import Depends

from apps.organizations.application.accept_organization_invitation import (
    AcceptOrganizationInvitation,
)
from apps.organizations.application.create_organization import CreateOrganization
from apps.organizations.application.get_organization import GetOrganizationById
from apps.organizations.application.invite_organization_member import InviteOrganizationMember
from apps.organizations.application.list_organization_members import ListOrganizationMembers
from apps.shared.domain.ports.public_events import PublicEventDispatcher
from shipster.platform.messaging.deps import get_public_event_dispatcher
from shipster.platform.persistence import ShipsterUnitOfWork, get_uow


async def get_create_organization(
    uow: ShipsterUnitOfWork = Depends(get_uow),
) -> CreateOrganization:
    return CreateOrganization(
        organizations=uow.organizations,
        members=uow.organization_members,
        users=uow.users,
    )


async def get_get_organization_by_id(
    uow: ShipsterUnitOfWork = Depends(get_uow),
) -> GetOrganizationById:
    return GetOrganizationById(organizations=uow.organizations)


async def get_list_organization_members(
    uow: ShipsterUnitOfWork = Depends(get_uow),
) -> ListOrganizationMembers:
    return ListOrganizationMembers(
        organizations=uow.organizations,
        members=uow.organization_members,
    )


async def get_invite_organization_member(
    uow: ShipsterUnitOfWork = Depends(get_uow),
    public_events: PublicEventDispatcher = Depends(get_public_event_dispatcher),
) -> InviteOrganizationMember:
    return InviteOrganizationMember(
        organizations=uow.organizations,
        users=uow.users,
        members=uow.organization_members,
        invitations=uow.organization_invitations,
        public_events=public_events,
    )


async def get_accept_organization_invitation(
    uow: ShipsterUnitOfWork = Depends(get_uow),
) -> AcceptOrganizationInvitation:
    return AcceptOrganizationInvitation(
        users=uow.users,
        members=uow.organization_members,
        invitations=uow.organization_invitations,
    )
