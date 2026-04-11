import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from apps.privacy.application.export_document import ExportDocumentBuilder
from apps.privacy.application.export_request_lifecycle import reconcile_ready_request
from apps.privacy.domain.entities import PrivacyExportRequest, PrivacyExportStatus
from apps.privacy.domain.ports.export_artifact_storage import ExportArtifactStorage
from apps.privacy.domain.ports.export_request_repository import ExportRequestRepository
from apps.privacy.domain.ports.subject_data_exporter import SubjectDataExporter

_LOG = logging.getLogger(__name__)


class ProcessPendingExports:
    def __init__(
        self,
        *,
        users_exporter: SubjectDataExporter,
        organizations_exporter: SubjectDataExporter,
        orders_exporter: SubjectDataExporter,
        requests: ExportRequestRepository,
        storage: ExportArtifactStorage,
        expiry_hours: int,
    ) -> None:
        self._requests = requests
        self._storage = storage
        self._expiry_hours = expiry_hours
        self._document_builder = ExportDocumentBuilder(
            users_exporter=users_exporter,
            organizations_exporter=organizations_exporter,
            orders_exporter=orders_exporter,
        )

    async def execute(self, *, limit: int = 10) -> None:
        ready = await self._requests.list_ready(limit=limit)
        for request in ready:
            await reconcile_ready_request(
                request=request,
                requests=self._requests,
                storage=self._storage,
            )

        pending = await self._requests.list_pending(limit=limit)
        if ready or pending:
            _LOG.debug(
                "privacy export worker: batch",
                extra={"ready_checked": len(ready), "pending_to_process": len(pending)},
            )
        for request in pending:
            await self._process_one(request)

    async def _process_one(self, request: PrivacyExportRequest) -> None:
        _LOG.info(
            "privacy export worker: processing request",
            extra={"export_request_id": str(request.id)},
        )
        started_at = datetime.now(UTC)
        await self._requests.save(
            replace(
                request,
                status=PrivacyExportStatus.PROCESSING,
                updated_at=started_at,
                expires_at=None,
                artifact_key=None,
                failure_reason=None,
            ),
        )
        try:
            payload = await self._document_builder.build_bytes(
                subject_user_id=request.subject_user_id,
                generated_at=started_at,
            )
            artifact = await self._storage.write_json_bytes(
                key=str(request.id),
                payload=payload,
            )
        except Exception as exc:
            _LOG.exception(
                "privacy export worker: export failed",
                extra={"export_request_id": str(request.id)},
            )
            await self._requests.save(
                replace(
                    request,
                    status=PrivacyExportStatus.FAILED,
                    updated_at=datetime.now(UTC),
                    expires_at=None,
                    artifact_key=None,
                    failure_reason=str(exc)[:1024],
                ),
            )
            return

        finished_at = datetime.now(UTC)
        await self._requests.save(
            replace(
                request,
                status=PrivacyExportStatus.READY,
                updated_at=finished_at,
                expires_at=finished_at + timedelta(hours=self._expiry_hours),
                artifact_key=artifact.key,
                failure_reason=None,
            ),
        )
        _LOG.info(
            "privacy export worker: export ready",
            extra={
                "export_request_id": str(request.id),
                "payload_bytes": len(payload),
            },
        )
