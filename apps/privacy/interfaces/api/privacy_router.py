from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse

from apps.auth.interfaces.dependencies import get_current_user_id
from apps.privacy.application.create_data_export import (
    CreateDataExport,
    DirectDataExportResult,
)
from apps.privacy.application.download_data_export import (
    DownloadDataExport,
)
from apps.privacy.application.get_data_export_status import GetDataExportStatus
from apps.privacy.application.list_export_lifecycle_events import ListExportLifecycleEvents
from apps.privacy.domain.errors import (
    PrivacyExportAccessDeniedError,
    PrivacyExportExpiredError,
    PrivacyExportFailedError,
    PrivacyExportNotFoundError,
    PrivacyExportNotReadyError,
    PrivacyExportSubjectNotFoundError,
)
from apps.privacy.interfaces.api.file_downloads import (
    build_direct_export_response,
    build_download_response,
)
from apps.privacy.interfaces.api.schemas import (
    ExportLifecycleEventResponse,
    ExportLifecycleEventsResponse,
    ExportRequestAcceptedResponse,
    ExportStatusResponse,
)
from apps.privacy.interfaces.dependencies import (
    get_create_data_export,
    get_download_data_export,
    get_get_data_export_status,
    get_list_export_lifecycle_events,
)

router = APIRouter(prefix="/privacy/exports", tags=["privacy"])


@router.post(
    "",
    response_model=None,
    responses={
        status.HTTP_202_ACCEPTED: {"model": ExportRequestAcceptedResponse},
        status.HTTP_404_NOT_FOUND: {"description": "not found"},
    },
)
async def create_export(
    user_id: UUID = Depends(get_current_user_id),
    use_case: CreateDataExport = Depends(get_create_data_export),
) -> FileResponse | JSONResponse:
    try:
        result = await use_case.execute(subject_user_id=user_id)
    except PrivacyExportSubjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not found",
        ) from None

    if isinstance(result, DirectDataExportResult):
        return build_direct_export_response(result)

    accepted = ExportRequestAcceptedResponse(
        request_id=result.request_id,
        status=result.status,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=accepted.model_dump(mode="json"),
    )


@router.get(
    "/{request_id}/events",
    response_model=ExportLifecycleEventsResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "not found"},
    },
)
async def list_export_lifecycle_events(
    request_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    use_case: ListExportLifecycleEvents = Depends(get_list_export_lifecycle_events),
) -> ExportLifecycleEventsResponse:
    try:
        result = await use_case.execute(
            request_id=request_id,
            subject_user_id=user_id,
            limit=limit,
            offset=offset,
        )
    except (PrivacyExportAccessDeniedError, PrivacyExportNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not found",
        ) from None

    return ExportLifecycleEventsResponse(
        events=[
            ExportLifecycleEventResponse(
                id=e.id,
                type=e.event_type.value,
                occurred_at=e.occurred_at,
                actor_user_id=e.actor_user_id,
            )
            for e in result.events
        ],
        total=result.total,
    )


@router.get(
    "/{request_id}",
    response_model=ExportStatusResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "not found"},
    },
)
async def get_export_status(
    request_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    use_case: GetDataExportStatus = Depends(get_get_data_export_status),
) -> ExportStatusResponse:
    try:
        export_request = await use_case.execute(
            request_id=request_id,
            subject_user_id=user_id,
        )
    except (PrivacyExportAccessDeniedError, PrivacyExportNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not found",
        ) from None

    return ExportStatusResponse(
        id=export_request.id,
        status=export_request.status.value,
        expires_at=export_request.expires_at,
    )


@router.get(
    "/{request_id}/download",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "not found"},
        status.HTTP_409_CONFLICT: {"description": "not ready or failed"},
        status.HTTP_410_GONE: {"description": "expired"},
    },
)
async def download_export(
    request_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    use_case: DownloadDataExport = Depends(get_download_data_export),
) -> FileResponse:
    try:
        downloadable = await use_case.execute(
            request_id=request_id,
            subject_user_id=user_id,
        )
    except (PrivacyExportAccessDeniedError, PrivacyExportNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not found",
        ) from None
    except PrivacyExportNotReadyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="not ready",
        ) from None
    except PrivacyExportFailedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="failed",
        ) from None
    except PrivacyExportExpiredError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="expired",
        ) from None

    return build_download_response(downloadable)
