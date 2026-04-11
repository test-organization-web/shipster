from uuid import UUID

from apps.privacy.application.export_request_lifecycle import reconcile_ready_request
from apps.privacy.domain.entities import PrivacyExportRequest
from apps.privacy.domain.errors import (
    PrivacyExportAccessDeniedError,
    PrivacyExportNotFoundError,
)
from apps.privacy.domain.ports.export_artifact_storage import ExportArtifactStorage
from apps.privacy.domain.ports.export_request_repository import ExportRequestRepository


class GetDataExportStatus:
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
    ) -> PrivacyExportRequest:
        request = await self._requests.get_by_id(request_id)
        if request is None:
            raise PrivacyExportNotFoundError()
        if request.subject_user_id != subject_user_id:
            raise PrivacyExportAccessDeniedError()
        return await reconcile_ready_request(
            request=request,
            requests=self._requests,
            storage=self._storage,
        )
