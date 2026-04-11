from uuid import UUID

from apps.users.domain.errors import UserNotFoundError
from apps.users.domain.ports.user_data_exporter import UserDataExporter
from apps.users.domain.ports.user_repository import UserRepository


class RepositoryUserDataExporter(UserDataExporter):
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def export_for_user(self, user_id: UUID) -> dict[str, object]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
            }
        }
