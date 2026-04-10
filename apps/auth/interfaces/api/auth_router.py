from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from apps.auth.application.authenticate_user import AuthenticateUser
from apps.auth.domain.errors import InvalidCredentialsError
from apps.auth.interfaces.api.schemas import LoginBody, RegisterBody, TokenResponse
from apps.auth.interfaces.dependencies import (
    get_authenticate_user,
    get_create_user,
    get_current_user_id,
)
from apps.users.application.create_user import CreateUser
from apps.users.application.get_user import GetUserById
from apps.users.domain.errors import (
    EmailAlreadyRegisteredError,
    UsernameAlreadyTakenError,
    UserNotFoundError,
)
from apps.users.interfaces.api.schemas import UserResponse
from apps.users.interfaces.dependencies import get_get_user_by_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterBody,
    use_case: CreateUser = Depends(get_create_user),
) -> UserResponse:
    try:
        user = await use_case.execute(
            email=body.email,
            username=body.username,
            plain_password=body.password,
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None
    except UsernameAlreadyTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        ) from None
    return UserResponse(id=user.id, email=user.email, username=user.username)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginBody,
    use_case: AuthenticateUser = Depends(get_authenticate_user),
) -> TokenResponse:
    try:
        access_token = await use_case.execute(email=body.email, password=body.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from None
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: UUID = Depends(get_current_user_id),
    use_case: GetUserById = Depends(get_get_user_by_id),
) -> UserResponse:
    try:
        user = await use_case.execute(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None
    return UserResponse(id=user.id, email=user.email, username=user.username)
