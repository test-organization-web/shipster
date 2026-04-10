"""FastAPI dependencies for shared messaging ports."""

import threading

from apps.messaging.application.public_event_dispatcher import (
    MessagePublisherPublicEventDispatcher,
)
from apps.messaging.domain.ports.messaging import MessagePublisher, MessageReceiver
from apps.messaging.factory import create_message_publisher, create_message_receiver
from apps.organizations.application.messaging.organization_invitation_created_handler import (
    OrganizationInvitationCreatedEmailHandler,
)
from apps.organizations.domain.ports.organization_invitation_created_handler import (
    OrganizationInvitationCreatedHandler,
)
from apps.shared.domain.ports.public_events import PublicEventDispatcher
from shipster.platform.notifications.deps import ensure_notification_sender

# `ensure_public_event_dispatcher()` composes another lazy singleton while holding
# the same guard, so this lock must be re-entrant.
_lock = threading.RLock()
_publisher: MessagePublisher | None = None
_receiver: MessageReceiver | None = None
_public_dispatcher: PublicEventDispatcher | None = None
_invitation_created_handler: OrganizationInvitationCreatedHandler | None = None


def ensure_message_publisher() -> MessagePublisher:
    """Lazy singleton (sync); use from schedulers and :func:`get_message_publisher`."""
    global _publisher
    if _publisher is None:
        with _lock:
            if _publisher is None:
                _publisher = create_message_publisher()
    return _publisher


def ensure_message_receiver() -> MessageReceiver:
    """Lazy singleton (sync); use from schedulers and :func:`get_message_receiver`."""
    global _receiver
    if _receiver is None:
        with _lock:
            if _receiver is None:
                _receiver = create_message_receiver()
    return _receiver


def ensure_public_event_dispatcher() -> PublicEventDispatcher:
    """Lazy singleton (sync); use from schedulers and :func:`get_public_event_dispatcher`."""
    global _public_dispatcher
    if _public_dispatcher is None:
        with _lock:
            if _public_dispatcher is None:
                _public_dispatcher = MessagePublisherPublicEventDispatcher(
                    ensure_message_publisher(),
                )
    return _public_dispatcher


def ensure_organization_invitation_created_handler() -> OrganizationInvitationCreatedHandler:
    """Sync lazy singleton; schedulers call this, FastAPI uses the async getter."""
    global _invitation_created_handler
    if _invitation_created_handler is None:
        with _lock:
            if _invitation_created_handler is None:
                _invitation_created_handler = OrganizationInvitationCreatedEmailHandler(
                    ensure_notification_sender(),
                )
    return _invitation_created_handler


async def get_message_publisher() -> MessagePublisher:
    return ensure_message_publisher()


async def get_message_receiver() -> MessageReceiver:
    return ensure_message_receiver()


async def get_public_event_dispatcher() -> PublicEventDispatcher:
    return ensure_public_event_dispatcher()


async def get_organization_invitation_created_handler() -> OrganizationInvitationCreatedHandler:
    return ensure_organization_invitation_created_handler()
