from typing import Protocol
from uuid import UUID


class SubjectDataExporter(Protocol):
    async def export_for_user(self, user_id: UUID) -> dict[str, object]:
        """Return the bounded-context export payload for one subject."""
