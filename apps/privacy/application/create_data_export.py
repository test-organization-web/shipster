import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from apps.privacy.application.export_document import ExportDocumentBuilder
from apps.privacy.domain.entities import PrivacyExportRequest, PrivacyExportStatus
from apps.privacy.domain.errors import PrivacyExportSubjectNotFoundError
from apps.privacy.domain.ports.export_artifact_storage import ExportArtifactStorage
from apps.privacy.domain.ports.export_request_repository import ExportRequestRepository
from apps.privacy.domain.ports.subject_data_exporter import SubjectDataExporter
from apps.users.domain.errors import UserNotFoundError

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DirectDataExportResult:
    filename: str
    media_type: str
    payload: bytes
    request_id: UUID


@dataclass(frozen=True, slots=True)
class AsyncDataExportResult:
    request_id: UUID
    status: str


class DirectExportEligibilityProbe(Protocol):
    async def is_direct_export_eligible(self, subject_user_id: UUID) -> bool:
        """Return whether a direct download is cheap and safe to attempt."""


class CreateDataExport:
    def __init__(
        self,
        *,
        users_exporter: SubjectDataExporter,
        organizations_exporter: SubjectDataExporter,
        orders_exporter: SubjectDataExporter,
        requests: ExportRequestRepository,
        storage: ExportArtifactStorage,
        direct_export_probe: DirectExportEligibilityProbe,
        direct_export_max_bytes: int,
        export_expiry_hours: int,
    ) -> None:
        self._users_exporter = users_exporter
        self._organizations_exporter = organizations_exporter
        self._orders_exporter = orders_exporter
        self._requests = requests
        self._storage = storage
        self._direct_export_probe = direct_export_probe
        self._direct_export_max_bytes = direct_export_max_bytes
        self._export_expiry_hours = export_expiry_hours
        self._document_builder = ExportDocumentBuilder(
            users_exporter=users_exporter,
            organizations_exporter=organizations_exporter,
            orders_exporter=orders_exporter,
        )

    async def execute(
        self,
        *,
        subject_user_id: UUID,
    ) -> DirectDataExportResult | AsyncDataExportResult:
        generated_at = datetime.now(UTC)
        try:
            is_direct_export_eligible = await self._direct_export_probe.is_direct_export_eligible(
                subject_user_id
            )
        except UserNotFoundError as exc:
            raise PrivacyExportSubjectNotFoundError(str(subject_user_id)) from exc

        if not is_direct_export_eligible:
            _LOG.info(
                "privacy export: subject not eligible for direct export, queuing async",
                extra={"subject_user_id": str(subject_user_id)},
            )
            return await self._create_async_request(
                subject_user_id=subject_user_id,
                generated_at=generated_at,
            )

        payload = await self._document_builder.build_bytes(
            subject_user_id=subject_user_id,
            generated_at=generated_at,
        )
        if len(payload) > self._direct_export_max_bytes:
            _LOG.info(
                "privacy export: direct payload over max bytes, queuing async",
                extra={
                    "subject_user_id": str(subject_user_id),
                    "payload_bytes": len(payload),
                    "direct_export_max_bytes": self._direct_export_max_bytes,
                },
            )
            return await self._create_async_request(
                subject_user_id=subject_user_id,
                generated_at=generated_at,
            )

        return await self._persist_direct_export(
            subject_user_id=subject_user_id,
            generated_at=generated_at,
            payload=payload,
        )

    async def _persist_direct_export(
        self,
        *,
        subject_user_id: UUID,
        generated_at: datetime,
        payload: bytes,
    ) -> DirectDataExportResult:
        request_id = uuid4()
        pending = PrivacyExportRequest(
            id=request_id,
            subject_user_id=subject_user_id,
            status=PrivacyExportStatus.PENDING,
            created_at=generated_at,
            updated_at=generated_at,
            expires_at=None,
            artifact_key=None,
            failure_reason=None,
        )
        await self._requests.save(pending)

        processing_at = datetime.now(UTC)
        processing = replace(
            pending,
            status=PrivacyExportStatus.PROCESSING,
            updated_at=processing_at,
            expires_at=None,
            artifact_key=None,
            failure_reason=None,
        )
        await self._requests.save(processing)

        artifact = await self._storage.write_json_bytes(key=str(request_id), payload=payload)
        finished_at = datetime.now(UTC)
        ready = replace(
            processing,
            status=PrivacyExportStatus.READY,
            updated_at=finished_at,
            expires_at=finished_at + timedelta(hours=self._export_expiry_hours),
            artifact_key=artifact.key,
            failure_reason=None,
        )
        await self._requests.save(ready)

        _LOG.info(
            "privacy export: direct export completed",
            extra={
                "export_request_id": str(request_id),
                "subject_user_id": str(subject_user_id),
                "payload_bytes": len(payload),
            },
        )
        return DirectDataExportResult(
            filename=f"shipster-export-{subject_user_id}.json",
            media_type="application/json",
            payload=payload,
            request_id=request_id,
        )

    async def _create_async_request(
        self,
        *,
        subject_user_id: UUID,
        generated_at: datetime,
    ) -> AsyncDataExportResult:
        request = PrivacyExportRequest(
            id=uuid4(),
            subject_user_id=subject_user_id,
            status=PrivacyExportStatus.PENDING,
            created_at=generated_at,
            updated_at=generated_at,
            expires_at=None,
            artifact_key=None,
            failure_reason=None,
        )
        await self._requests.save(request)
        _LOG.info(
            "privacy export: async export request created",
            extra={
                "export_request_id": str(request.id),
                "subject_user_id": str(subject_user_id),
            },
        )
        return AsyncDataExportResult(request_id=request.id, status=request.status.value)
