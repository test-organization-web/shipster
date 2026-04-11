from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from apps.auth.interfaces.dependencies import get_current_user_id
from apps.privacy.application.get_erasure_status import GetErasureStatus
from apps.privacy.application.request_erasure import RequestErasure
from apps.privacy.domain.errors import (
    PrivacyErasureConflictError,
    PrivacyErasureNotFoundError,
    PrivacyErasureSubjectNotFoundError,
)
from apps.privacy.interfaces.api.erasure_schemas import (
    ErasureRequestAcceptedResponse,
    ErasureStatusResponse,
)
from apps.privacy.interfaces.dependencies import get_get_erasure_status, get_request_erasure

router = APIRouter(prefix="/privacy/erasure-requests", tags=["privacy"])


@router.post(
    "",
    responses={
        status.HTTP_202_ACCEPTED: {"model": ErasureRequestAcceptedResponse},
        status.HTTP_404_NOT_FOUND: {"description": "not found"},
        status.HTTP_409_CONFLICT: {"description": "erasure already in progress"},
    },
)
async def request_erasure(
    user_id: UUID = Depends(get_current_user_id),
    use_case: RequestErasure = Depends(get_request_erasure),
) -> JSONResponse:
    try:
        result = await use_case.execute(subject_user_id=user_id)
    except PrivacyErasureSubjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not found",
        ) from None
    except PrivacyErasureConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="erasure already in progress",
        ) from None

    body = ErasureRequestAcceptedResponse(
        request_id=result.id,
        status=result.status.value,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=body.model_dump(mode="json"),
    )


@router.get(
    "/{request_id}",
    response_model=ErasureStatusResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "not found"},
    },
)
async def get_erasure_status(
    request_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    use_case: GetErasureStatus = Depends(get_get_erasure_status),
) -> ErasureStatusResponse:
    try:
        erasure = await use_case.execute(request_id=request_id, subject_user_id=user_id)
    except PrivacyErasureNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not found",
        ) from None

    return ErasureStatusResponse(
        id=erasure.id,
        status=erasure.status.value,
        created_at=erasure.created_at,
        updated_at=erasure.updated_at,
        failure_reason=erasure.failure_reason,
    )
