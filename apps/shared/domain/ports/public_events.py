"""Public integration events — implemented in :mod:`shipster.platform` (composition root)."""

from typing import Any, Protocol

from apps.shared.domain.event import Event


class PublicEventDispatcher(Protocol):
    """Dispatch named events for external consumers (streams, webhooks, outbox workers)."""

    async def dispatch(self, event: Event[Any]) -> None:
        """Emit a typed :class:`~apps.shared.domain.event.Event` envelope."""
