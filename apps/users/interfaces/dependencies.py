from functools import lru_cache

from fastapi import Depends

from apps.users.application.get_user import GetUserById
from apps.users.infrastructure.security.pbkdf2_password_hasher import Pbkdf2PasswordHasher
from shipster.platform.persistence import ShipsterUnitOfWork, get_uow


@lru_cache(maxsize=1)
def _password_hasher_singleton() -> Pbkdf2PasswordHasher:
    return Pbkdf2PasswordHasher()


async def get_password_hasher() -> Pbkdf2PasswordHasher:
    return _password_hasher_singleton()


async def get_get_user_by_id(
    uow: ShipsterUnitOfWork = Depends(get_uow),
) -> GetUserById:
    return GetUserById(users=uow.users)
