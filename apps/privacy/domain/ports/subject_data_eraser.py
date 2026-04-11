from typing import Protocol
from uuid import UUID


class SubjectDataEraser(Protocol):
    async def erase_for_user(self, user_id: UUID) -> None:
        """Erase or anonymize this bounded context's data for the subject."""
