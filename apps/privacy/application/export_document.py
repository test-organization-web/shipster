import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from apps.privacy.domain.errors import PrivacyExportSubjectNotFoundError
from apps.privacy.domain.ports.subject_data_exporter import SubjectDataExporter
from apps.users.domain.errors import UserNotFoundError

_LOG = logging.getLogger(__name__)


def build_export_document(
    *,
    subject_user_id: UUID,
    generated_at: datetime,
    users_payload: dict[str, object],
    organizations_payload: dict[str, object],
    orders_payload: dict[str, object],
) -> dict[str, object]:
    return {
        "meta": {
            "subject_user_id": str(subject_user_id),
            "generated_at": generated_at.isoformat(),
            "schema_version": 1,
        },
        "users": users_payload,
        "organizations": organizations_payload,
        "orders": orders_payload,
    }


class ExportDocumentBuilder:
    def __init__(
        self,
        *,
        users_exporter: SubjectDataExporter,
        organizations_exporter: SubjectDataExporter,
        orders_exporter: SubjectDataExporter,
    ) -> None:
        self._users_exporter = users_exporter
        self._organizations_exporter = organizations_exporter
        self._orders_exporter = orders_exporter

    async def build_bytes(
        self,
        *,
        subject_user_id: UUID,
        generated_at: datetime | None = None,
    ) -> bytes:
        export_generated_at = generated_at or datetime.now(UTC)
        try:
            users_payload = await self._users_exporter.export_for_user(subject_user_id)
            organizations_payload = await self._organizations_exporter.export_for_user(
                subject_user_id,
            )
            orders_payload = await self._orders_exporter.export_for_user(subject_user_id)
        except UserNotFoundError as exc:
            raise PrivacyExportSubjectNotFoundError(str(subject_user_id)) from exc

        document = build_export_document(
            subject_user_id=subject_user_id,
            generated_at=export_generated_at,
            users_payload=users_payload,
            organizations_payload=organizations_payload,
            orders_payload=orders_payload,
        )
        raw = json.dumps(document, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        _LOG.debug(
            "privacy export: document built",
            extra={"subject_user_id": str(subject_user_id), "payload_bytes": len(raw)},
        )
        return raw
