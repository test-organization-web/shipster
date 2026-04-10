from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from apps.auth.interfaces.dependencies import get_current_user_id
from apps.organizations.application.accept_organization_invitation import (
    AcceptOrganizationInvitation,
)
from apps.organizations.application.create_organization import CreateOrganization
from apps.organizations.application.get_organization import GetOrganizationById
from apps.organizations.application.invite_organization_member import InviteOrganizationMember
from apps.organizations.application.list_organization_members import ListOrganizationMembers
from apps.organizations.domain.errors import (
    InvitationAlreadyUsedError,
    InvitationEmailMismatchError,
    InvitationExpiredError,
    InvitationNotFoundError,
    MemberAlreadyExistsError,
    NotOrganizationMemberError,
    OrganizationNotFoundError,
    PendingInvitationExistsError,
    SlugAlreadyTakenError,
)
from apps.organizations.interfaces.api.schemas import (
    AcceptOrganizationInvitationBody,
    CreateOrganizationBody,
    InvitationCreatedResponse,
    InviteOrganizationMemberBody,
    OrganizationMemberResponse,
    OrganizationResponse,
)
from apps.organizations.interfaces.dependencies import (
    get_accept_organization_invitation,
    get_create_organization,
    get_get_organization_by_id,
    get_invite_organization_member,
    get_list_organization_members,
)
from apps.users.domain.errors import UserNotFoundError

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: CreateOrganizationBody,
    creator_user_id: UUID = Depends(get_current_user_id),
    use_case: CreateOrganization = Depends(get_create_organization),
) -> OrganizationResponse:
    try:
        organization = await use_case.execute(
            name=body.name,
            slug=body.slug,
            creator_user_id=creator_user_id,
        )
    except SlugAlreadyTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slug already taken",
        ) from None
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
    )


@router.post(
    "/invitations/accept",
    response_model=OrganizationMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def accept_organization_invitation(
    body: AcceptOrganizationInvitationBody,
    user_id: UUID = Depends(get_current_user_id),
    use_case: AcceptOrganizationInvitation = Depends(get_accept_organization_invitation),
) -> OrganizationMemberResponse:
    try:
        member = await use_case.execute(raw_token=body.token, accepting_user_id=user_id)
    except InvitationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        ) from None
    except InvitationExpiredError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired",
        ) from None
    except InvitationAlreadyUsedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation was already used or revoked",
        ) from None
    except InvitationEmailMismatchError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation is for a different email address",
        ) from None
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None
    return OrganizationMemberResponse(
        id=member.id,
        organization_id=member.organization_id,
        user_id=member.user_id,
    )


@router.get("/{organization_id}/members", response_model=list[OrganizationMemberResponse])
async def list_organization_members(
    organization_id: UUID,
    use_case: ListOrganizationMembers = Depends(get_list_organization_members),
) -> list[OrganizationMemberResponse]:
    try:
        members = await use_case.execute(organization_id)
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        ) from None
    return [
        OrganizationMemberResponse(
            id=m.id,
            organization_id=m.organization_id,
            user_id=m.user_id,
        )
        for m in members
    ]


@router.post(
    "/{organization_id}/invitations",
    response_model=InvitationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_organization_member(
    organization_id: UUID,
    body: InviteOrganizationMemberBody,
    inviter_id: UUID = Depends(get_current_user_id),
    use_case: InviteOrganizationMember = Depends(get_invite_organization_member),
) -> InvitationCreatedResponse:
    try:
        result = await use_case.execute(
            organization_id=organization_id,
            email=str(body.email),
            invited_by_user_id=inviter_id,
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        ) from None
    except NotOrganizationMemberError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization members can send invitations",
        ) from None
    except PendingInvitationExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists for this email",
        ) from None
    except MemberAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization",
        ) from None
    inv = result.invitation
    return InvitationCreatedResponse(
        invitation_id=inv.id,
        email=inv.email,
        expires_at=inv.expires_at,
        token=result.raw_token,
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    use_case: GetOrganizationById = Depends(get_get_organization_by_id),
) -> OrganizationResponse:
    try:
        organization = await use_case.execute(organization_id)
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        ) from None

    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
    )
