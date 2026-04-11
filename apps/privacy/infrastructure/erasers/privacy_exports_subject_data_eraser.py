import logging
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from apps.privacy.domain.entities import PrivacyExportStatus
from apps.privacy.domain.ports.export_artifact_storage import ExportArtifactStorage
from apps.privacy.domain.ports.export_request_repository import ExportRequestRepository

_LOG = logging.getLogger(__name__)


class PrivacyExportsSubjectDataEraser:
    """Expire all export requests for a subject and remove stored artifacts."""

    def __init__(
        self,
        *,
        export_requests: ExportRequestRepository,
        storage: ExportArtifactStorage,
    ) -> None:
        self._export_requests = export_requests
        self._storage = storage

    async def erase_for_user(self, user_id: UUID) -> None:
        exports = await self._export_requests.list_all_for_subject_user(user_id)
        _LOG.info(
            "privacy erasure: expiring subject export requests",
            extra={"subject_user_id": str(user_id), "export_count": len(exports)},
        )
        for exp in exports:
            if exp.artifact_key is not None:
                try:
                    await self._storage.delete(exp.artifact_key)
                except (FileNotFoundError, OSError) as exc:
                    _LOG.warning(
                        "privacy erasure: failed to delete export artifact",
                        extra={
                            "subject_user_id": str(user_id),
                            "export_request_id": str(exp.id),
                            "exc_type": type(exc).__name__,
                        },
                    )
            now = datetime.now(UTC)
            await self._export_requests.save(
                replace(
                    exp,
                    status=PrivacyExportStatus.EXPIRED,
                    updated_at=now,
                    expires_at=None,
                    artifact_key=None,
                    failure_reason=None,
                ),
            )
