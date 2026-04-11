import logging
from dataclasses import replace
from datetime import UTC, datetime

from apps.privacy.domain.entities import PrivacyExportRequest, PrivacyExportStatus
from apps.privacy.domain.ports.export_artifact_storage import ExportArtifactStorage
from apps.privacy.domain.ports.export_request_repository import ExportRequestRepository

_LOG = logging.getLogger(__name__)

_MISSING_ARTIFACT_REASON = "Export artifact is unavailable."


def is_request_expired(request: PrivacyExportRequest) -> bool:
    return (
        request.status is PrivacyExportStatus.READY
        and request.expires_at is not None
        and request.expires_at <= datetime.now(UTC)
    )


async def expire_request(
    *,
    request: PrivacyExportRequest,
    requests: ExportRequestRepository,
    storage: ExportArtifactStorage,
) -> PrivacyExportRequest:
    if request.artifact_key is not None:
        await storage.delete(request.artifact_key)
    expired_request = replace(
        request,
        status=PrivacyExportStatus.EXPIRED,
        updated_at=datetime.now(UTC),
        artifact_key=None,
    )
    await requests.save(expired_request)
    _LOG.info(
        "privacy export: request expired",
        extra={"export_request_id": str(expired_request.id)},
    )
    return expired_request


async def fail_request(
    *,
    request: PrivacyExportRequest,
    requests: ExportRequestRepository,
    storage: ExportArtifactStorage,
    reason: str,
) -> PrivacyExportRequest:
    if request.artifact_key is not None:
        await storage.delete(request.artifact_key)
    failed_request = replace(
        request,
        status=PrivacyExportStatus.FAILED,
        updated_at=datetime.now(UTC),
        expires_at=None,
        artifact_key=None,
        failure_reason=reason,
    )
    await requests.save(failed_request)
    _LOG.warning(
        "privacy export: request marked failed",
        extra={
            "export_request_id": str(failed_request.id),
            "reason": reason[:256],
        },
    )
    return failed_request


async def reconcile_ready_request(
    *,
    request: PrivacyExportRequest,
    requests: ExportRequestRepository,
    storage: ExportArtifactStorage,
) -> PrivacyExportRequest:
    if request.status is not PrivacyExportStatus.READY:
        return request
    if is_request_expired(request):
        return await expire_request(request=request, requests=requests, storage=storage)
    if request.artifact_key is None:
        return await fail_request(
            request=request,
            requests=requests,
            storage=storage,
            reason=_MISSING_ARTIFACT_REASON,
        )
    try:
        await storage.open_for_download(request.artifact_key)
    except (FileNotFoundError, OSError):
        return await fail_request(
            request=request,
            requests=requests,
            storage=storage,
            reason=_MISSING_ARTIFACT_REASON,
        )
    return request
