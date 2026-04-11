from functools import lru_cache
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from apps.auth.application.authenticate_user import AuthenticateUser
from apps.auth.application.change_password import ChangePassword
from apps.auth.application.complete_password_reset import CompletePasswordReset
from apps.auth.application.process_password_reset_notifications import (
    ProcessPasswordResetNotifications,
)
from apps.auth.application.request_password_reset import RequestPasswordReset
from apps.auth.application.verify_access_token import VerifyAccessToken
from apps.auth.domain.errors import InvalidTokenError
from apps.auth.infrastructure.jwt_access_token import JwtAccessTokenService
from apps.users.application.create_user import CreateUser
from apps.users.infrastructure.security.pbkdf2_password_hasher import Pbkdf2PasswordHasher
from apps.users.interfaces.dependencies import get_password_hasher
from shipster.platform.notifications.deps import ensure_notification_sender
from shipster.platform.persistence import ShipsterUnitOfWork, get_uow
from shipster.platform.settings import GlobalSettings, get_global_settings

_http_bearer = HTTPBearer()


def build_process_password_reset_notifications(
    *,
    uow: ShipsterUnitOfWork,
    settings: GlobalSettings,
) -> ProcessPasswordResetNotifications:
    return ProcessPasswordResetNotifications(
        reset_tokens=uow.password_reset_tokens,
        users=uow.users,
        notification_sender=ensure_notification_sender(),
        password_reset_url_template=settings.password_reset_url_template,
    )


def _jwt_secret() -> str:
    return get_global_settings().jwt_secret


@lru_cache(maxsize=1)
def _access_token_service_singleton() -> JwtAccessTokenService:
    return JwtAccessTokenService(secret=_jwt_secret())


async def get_access_token_service() -> JwtAccessTokenService:
    return _access_token_service_singleton()


async def get_create_user(
    uow: ShipsterUnitOfWork = Depends(get_uow),
    password_hasher: Pbkdf2PasswordHasher = Depends(get_password_hasher),
) -> CreateUser:
    return CreateUser(users=uow.users, password_hasher=password_hasher)


async def get_authenticate_user(
    uow: ShipsterUnitOfWork = Depends(get_uow),
    password_hasher: Pbkdf2PasswordHasher = Depends(get_password_hasher),
    tokens: JwtAccessTokenService = Depends(get_access_token_service),
) -> AuthenticateUser:
    return AuthenticateUser(
        users=uow.users,
        password_hasher=password_hasher,
        tokens=tokens,
    )


async def get_change_password(
    uow: ShipsterUnitOfWork = Depends(get_uow),
    password_hasher: Pbkdf2PasswordHasher = Depends(get_password_hasher),
) -> ChangePassword:
    return ChangePassword(users=uow.users, password_hasher=password_hasher)


async def get_request_password_reset(
    uow: ShipsterUnitOfWork = Depends(get_uow),
) -> RequestPasswordReset:
    return RequestPasswordReset(
        users=uow.users,
        reset_tokens=uow.password_reset_tokens,
    )


async def get_complete_password_reset(
    uow: ShipsterUnitOfWork = Depends(get_uow),
    password_hasher: Pbkdf2PasswordHasher = Depends(get_password_hasher),
) -> CompletePasswordReset:
    return CompletePasswordReset(
        users=uow.users,
        reset_tokens=uow.password_reset_tokens,
        password_hasher=password_hasher,
    )


async def get_verify_access_token(
    tokens: JwtAccessTokenService = Depends(get_access_token_service),
) -> VerifyAccessToken:
    return VerifyAccessToken(tokens=tokens)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_http_bearer),
    verify: VerifyAccessToken = Depends(get_verify_access_token),
) -> UUID:
    try:
        return await run_in_threadpool(verify.execute, credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from None
