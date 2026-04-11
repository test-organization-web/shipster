from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from apps.auth.application.authenticate_user import AuthenticateUser
from apps.auth.application.change_password import ChangePassword
from apps.auth.application.complete_password_reset import CompletePasswordReset
from apps.auth.application.request_password_reset import RequestPasswordReset
from apps.auth.domain.errors import InvalidCredentialsError, InvalidPasswordResetTokenError
from apps.auth.interfaces.api.schemas import (
    ChangePasswordBody,
    LoginBody,
    PasswordResetCompleteBody,
    PasswordResetRequestAccepted,
    PasswordResetRequestBody,
    RegisterBody,
    TokenResponse,
)
from apps.auth.interfaces.dependencies import (
    get_authenticate_user,
    get_change_password,
    get_complete_password_reset,
    get_create_user,
    get_current_user_id,
    get_request_password_reset,
)
from apps.organizations.application.list_user_organizations import ListUserOrganizations
from apps.organizations.interfaces.dependencies import get_list_user_organizations
from apps.users.application.create_user import CreateUser
from apps.users.application.get_user import GetUserById
from apps.users.domain.errors import (
    EmailAlreadyRegisteredError,
    InvalidCurrentPasswordError,
    UsernameAlreadyTakenError,
    UserNotFoundError,
)
from apps.users.interfaces.api.schemas import UserOrganizationResponse, UserResponse
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


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_password_reset(
    body: PasswordResetRequestBody,
    use_case: RequestPasswordReset = Depends(get_request_password_reset),
) -> PasswordResetRequestAccepted:
    await use_case.execute(email=str(body.email))
    return PasswordResetRequestAccepted()


@router.post("/password-reset/complete", status_code=status.HTTP_204_NO_CONTENT)
async def complete_password_reset(
    body: PasswordResetCompleteBody,
    use_case: CompletePasswordReset = Depends(get_complete_password_reset),
) -> None:
    try:
        await use_case.execute(raw_token=body.token, new_password=body.new_password)
    except InvalidPasswordResetTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link",
        ) from None


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    body: ChangePasswordBody,
    user_id: UUID = Depends(get_current_user_id),
    use_case: ChangePassword = Depends(get_change_password),
) -> None:
    try:
        await use_case.execute(
            user_id=user_id,
            current_password=body.current_password,
            new_password=body.new_password,
        )
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None
    except InvalidCurrentPasswordError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        ) from None


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: UUID = Depends(get_current_user_id),
    use_case: GetUserById = Depends(get_get_user_by_id),
    list_orgs: ListUserOrganizations = Depends(get_list_user_organizations),
) -> UserResponse:
    try:
        user = await use_case.execute(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None
    summaries = await list_orgs.execute(user_id)
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        organizations=[
            UserOrganizationResponse(
                organization_id=s.organization_id,
                organization_name=s.organization_name,
            )
            for s in summaries
        ],
    )
