"""Plug for side effects when an organization invitation public event is consumed."""

from typing import Protocol

from apps.organizations.domain.organization_public_events import (
    OrganizationInvitationCreatedPayload,
)


class OrganizationInvitationCreatedHandler(Protocol):
    """Application-specific handling (email, webhooks, etc.) for invitation-created events."""

    async def handle(self, payload: OrganizationInvitationCreatedPayload) -> None:
        """Process a single decoded payload from the stream."""
