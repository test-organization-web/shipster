from uuid import UUID


class OrderSubjectDataEraser:
    """No order-scoped PII beyond nullable ``user_id`` in v1; erasure is a no-op here."""

    async def erase_for_user(self, user_id: UUID) -> None:
        _ = user_id
