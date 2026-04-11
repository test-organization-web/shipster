from typing import Protocol
from uuid import UUID


class OrganizationDataExporter(Protocol):
    async def export_for_user(self, user_id: UUID) -> dict[str, object]:
        """Return the user-owned organizations-context export payload."""
