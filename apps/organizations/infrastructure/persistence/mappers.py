from apps.organizations.domain.entities import (
    InvitationStatus,
    Organization,
    OrganizationInvitation,
    OrganizationMember,
)
from apps.organizations.infrastructure.persistence.schema.organization import OrganizationORM
from apps.organizations.infrastructure.persistence.schema.organization_invitation import (
    OrganizationInvitationORM,
)
from apps.organizations.infrastructure.persistence.schema.organization_member import (
    OrganizationMemberORM,
)


def organization_row_to_domain(row: OrganizationORM) -> Organization:
    return Organization(
        id=row.id,
        name=row.name,
        slug=row.slug,
    )


def organization_domain_to_row(organization: Organization) -> OrganizationORM:
    return OrganizationORM(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
    )


def organization_member_row_to_domain(row: OrganizationMemberORM) -> OrganizationMember:
    return OrganizationMember(
        id=row.id,
        organization_id=row.organization_id,
        user_id=row.user_id,
    )


def organization_member_domain_to_row(member: OrganizationMember) -> OrganizationMemberORM:
    return OrganizationMemberORM(
        id=member.id,
        organization_id=member.organization_id,
        user_id=member.user_id,
    )


def organization_invitation_row_to_domain(row: OrganizationInvitationORM) -> OrganizationInvitation:
    return OrganizationInvitation(
        id=row.id,
        organization_id=row.organization_id,
        email=row.email,
        token_hash=row.token_hash,
        invited_by_user_id=row.invited_by_user_id,
        created_at=row.created_at,
        expires_at=row.expires_at,
        status=InvitationStatus(row.status),
        accepted_at=row.accepted_at,
    )


def organization_invitation_domain_to_row(
    invitation: OrganizationInvitation,
) -> OrganizationInvitationORM:
    return OrganizationInvitationORM(
        id=invitation.id,
        organization_id=invitation.organization_id,
        email=invitation.email,
        token_hash=invitation.token_hash,
        invited_by_user_id=invitation.invited_by_user_id,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        status=invitation.status.value,
    )
