import logging
from dataclasses import dataclass
from uuid import UUID

from apps.privacy.application.export_request_lifecycle import (
    fail_request,
    reconcile_ready_request,
)
from apps.privacy.domain.entities import PrivacyExportStatus
from apps.privacy.domain.errors import (
    PrivacyExportAccessDeniedError,
    PrivacyExportExpiredError,
    PrivacyExportFailedError,
    PrivacyExportNotFoundError,
    PrivacyExportNotReadyError,
)
from apps.privacy.domain.ports.export_artifact_storage import ExportArtifactStorage
from apps.privacy.domain.ports.export_request_repository import ExportRequestRepository

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DownloadableExport:
    locator: str
    filename: str
    media_type: str


class DownloadDataExport:
    def __init__(
        self,
        *,
        requests: ExportRequestRepository,
        storage: ExportArtifactStorage,
    ) -> None:
        self._requests = requests
        self._storage = storage

    async def execute(
        self,
        *,
        request_id: UUID,
        subject_user_id: UUID,
    ) -> DownloadableExport:
        request = await self._requests.get_by_id(request_id)
        if request is None:
            raise PrivacyExportNotFoundError()
        if request.subject_user_id != subject_user_id:
            raise PrivacyExportAccessDeniedError()
        request = await reconcile_ready_request(
            request=request,
            requests=self._requests,
            storage=self._storage,
        )
        if request.status is PrivacyExportStatus.EXPIRED:
            raise PrivacyExportExpiredError()
        if request.status in {
            PrivacyExportStatus.PENDING,
            PrivacyExportStatus.PROCESSING,
        }:
            raise PrivacyExportNotReadyError()
        if request.status is PrivacyExportStatus.FAILED:
            raise PrivacyExportFailedError()
        if request.artifact_key is None:
            raise PrivacyExportFailedError()

        try:
            artifact = await self._storage.open_for_download(request.artifact_key)
        except (FileNotFoundError, OSError) as exc:
            await fail_request(
                request=request,
                requests=self._requests,
                storage=self._storage,
                reason="Export artifact is unavailable.",
            )
            raise PrivacyExportFailedError() from exc

        _LOG.info(
            "privacy export: download authorized",
            extra={"export_request_id": str(request_id)},
        )
        return DownloadableExport(
            locator=artifact.locator,
            filename=f"shipster-export-{request.id}.json",
            media_type=artifact.media_type,
        )
