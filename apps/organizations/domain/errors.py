class OrganizationNotFoundError(Exception):
    """Raised when an organization cannot be loaded by identifier."""


class SlugAlreadyTakenError(Exception):
    """Raised when creation uses a slug that already exists."""


class MemberAlreadyExistsError(Exception):
    """Raised when adding a user who is already a member of the organization."""


class NotOrganizationMemberError(Exception):
    """Raised when the acting user is not a member of the organization."""


class PendingInvitationExistsError(Exception):
    """Raised when a pending invitation already exists for this email and organization."""


class InvitationNotFoundError(Exception):
    """Raised when no invitation matches the given token."""


class InvitationExpiredError(Exception):
    """Raised when an invitation is past its expiry time."""


class InvitationAlreadyUsedError(Exception):
    """Raised when an invitation was already accepted or revoked."""


class InvitationEmailMismatchError(Exception):
    """Raised when the authenticated user's email does not match the invitation."""
