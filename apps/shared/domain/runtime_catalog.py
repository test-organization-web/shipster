"""Single source of truth for messaging topics, message payload type tags, and scheduler job ids."""

from dataclasses import dataclass
from typing import Final

from apps.shared.domain.ports.stream_consumer_params import StreamConsumerParams


@dataclass(frozen=True, slots=True)
class MessagingTopics:
    """Broker topics: RabbitMQ routing key, Redis stream suffix after ``shipster:msg:``."""

    users_password_reset_requested: str


MESSAGING_TOPICS: Final[MessagingTopics] = MessagingTopics(
    users_password_reset_requested="users.password_reset_requested",
)


@dataclass(frozen=True, slots=True)
class MessagePayloadTypes:
    """``type`` field in JSON message bodies (discriminator for consumers)."""

    password_reset_requested: str


MESSAGE_PAYLOAD_TYPES: Final[MessagePayloadTypes] = MessagePayloadTypes(
    password_reset_requested="password_reset_requested",
)


AUTH_PASSWORD_RESET_REQUESTED_POLL: Final[StreamConsumerParams] = StreamConsumerParams(
    subscription="auth.users_password_reset_requested",
    consumer_id="shipster-scheduler",
    max_messages=20,
    block_ms=500,
)


@dataclass(frozen=True, slots=True)
class PrivacyIntervalJobIds:
    """APScheduler :attr:`IntervalJobSpec.id` values for the privacy bounded context."""

    process_pending_exports: str
    process_pending_erasure_requests: str


@dataclass(frozen=True, slots=True)
class AuthIntervalJobIds:
    """APScheduler :attr:`IntervalJobSpec.id` values for the auth bounded context."""

    process_pending_password_reset_notifications: str


@dataclass(frozen=True, slots=True)
class IntervalJobIds:
    privacy: PrivacyIntervalJobIds
    auth: AuthIntervalJobIds


INTERVAL_JOB_IDS: Final[IntervalJobIds] = IntervalJobIds(
    privacy=PrivacyIntervalJobIds(
        process_pending_exports="privacy.process_pending_exports",
        process_pending_erasure_requests="privacy.process_pending_erasure_requests",
    ),
    auth=AuthIntervalJobIds(
        process_pending_password_reset_notifications=(
            "auth.process_pending_password_reset_notifications"
        ),
    ),
)
