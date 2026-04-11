from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class PrivacyExportStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


class PrivacyExportLifecycleEventType(StrEnum):
    EXPORT_REQUEST_CREATED = "export_request_created"
    EXPORT_PROCESSING_STARTED = "export_processing_started"
    EXPORT_READY = "export_ready"
    EXPORT_FAILED = "export_failed"
    EXPORT_EXPIRED = "export_expired"


@dataclass(frozen=True, slots=True)
class PrivacyExportLifecycleEvent:
    id: UUID
    export_request_id: UUID
    event_type: PrivacyExportLifecycleEventType
    occurred_at: datetime
    actor_user_id: UUID | None


@dataclass(frozen=True, slots=True)
class PrivacyExportRequest:
    id: UUID
    subject_user_id: UUID
    status: PrivacyExportStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    artifact_key: str | None
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class PrivacyExportArtifact:
    key: str
    filename: str
    media_type: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class PrivacyDownloadableArtifact:
    """How to read bytes for one stored export; ``locator`` is opaque to domain/application."""

    locator: str
    media_type: str


class PrivacyErasureStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PrivacyErasureRequest:
    id: UUID
    subject_user_id: UUID
    status: PrivacyErasureStatus
    created_at: datetime
    updated_at: datetime
    failure_reason: str | None
