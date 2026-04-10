from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from apps.users.application.get_user import GetUserById
from apps.users.domain.errors import UserNotFoundError
from apps.users.interfaces.api.schemas import UserResponse
from apps.users.interfaces.dependencies import get_get_user_by_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
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
