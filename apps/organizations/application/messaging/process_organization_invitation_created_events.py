"""Poll the invitation-created stream and invoke the configured handler."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from uuid import UUID

from apps.messaging.domain.ports.messaging import MessageReceiver
from apps.organizations.domain.organization_public_events import (
    ORGANIZATION_INVITATION_CREATED_TOPIC,
    OrganizationInvitationCreatedPayload,
)
from apps.organizations.domain.ports.organization_invitation_created_handler import (
    OrganizationInvitationCreatedHandler,
)
from apps.shared.domain.ports.stream_consumer_params import StreamConsumerParams

_LOG = logging.getLogger(__name__)


class ProcessOrganizationInvitationCreatedEvents:
    """Pull messages for ``ORGANIZATION_INVITATION_CREATED_TOPIC`` and dispatch to the plug."""

    def __init__(
        self,
        receiver: MessageReceiver,
        handler: OrganizationInvitationCreatedHandler,
        *,
        params: StreamConsumerParams,
        topic: str = ORGANIZATION_INVITATION_CREATED_TOPIC,
    ) -> None:
        self._receiver = receiver
        self._handler = handler
        self._topic = topic
        self._subscription = params.subscription
        self._consumer_id = params.consumer_id
        self._max_messages = params.max_messages
        self._block_ms = params.block_ms

    async def execute(self) -> None:
        messages = await self._receiver.pull(
            self._topic,
            subscription=self._subscription,
            consumer_id=self._consumer_id,
            max_messages=self._max_messages,
            block_ms=self._block_ms,
        )
        for msg in messages:
            try:
                payload = self._parse_message_body(msg.body)
                await self._handler.handle(payload)
            except Exception:
                _LOG.exception(
                    "Failed to process invitation-created message; will not ack (id=%s)",
                    msg.id,
                )
                continue
            await self._receiver.acknowledge(
                self._topic,
                subscription=self._subscription,
                message_ids=[msg.id],
            )

    @staticmethod
    def _parse_message_body(body: bytes) -> OrganizationInvitationCreatedPayload:
        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, dict):
            msg = "Event body must be a JSON object"
            raise ValueError(msg)
        if data.get("topic") != ORGANIZATION_INVITATION_CREATED_TOPIC:
            msg = f"Unexpected event topic: {data.get('topic')!r}"
            raise ValueError(msg)
        raw = data.get("payload")
        if not isinstance(raw, dict):
            msg = "Event envelope missing payload object"
            raise ValueError(msg)
        invited_by = raw.get("invited_by_user_id")
        return OrganizationInvitationCreatedPayload(
            invitation_id=UUID(str(raw["invitation_id"])),
            organization_id=UUID(str(raw["organization_id"])),
            organization_name=str(raw["organization_name"]),
            email=str(raw["email"]),
            invited_by_user_id=None if invited_by is None else UUID(str(invited_by)),
            expires_at=ProcessOrganizationInvitationCreatedEvents._parse_datetime(
                raw["expires_at"],
            ),
            token=str(raw["token"]),
        )

    @staticmethod
    def _parse_datetime(value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        msg = f"Invalid expires_at: {value!r}"
        raise TypeError(msg)


def create_invitation_created_processor(
    receiver: MessageReceiver,
    handler: OrganizationInvitationCreatedHandler,
    params: StreamConsumerParams,
) -> ProcessOrganizationInvitationCreatedEvents:
    """Build a one-shot processor (use :func:`get_or_create_singleton` for scheduled jobs)."""
    return ProcessOrganizationInvitationCreatedEvents(receiver, handler, params=params)
