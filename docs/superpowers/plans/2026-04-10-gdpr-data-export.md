# GDPR Data Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new `apps/privacy` bounded context that supports hybrid GDPR data export: immediate file download for small exports and tracked async export generation for larger exports.

**Architecture:** Keep privacy orchestration inside `apps/privacy`, and keep each existing bounded context responsible for exporting its own data through small, focused ports. Wire the privacy router, persistence, and scheduler from `shipster.platform`, while keeping domain/application code free of `shipster` imports.

**Tech Stack:** FastAPI, SQLAlchemy async session/UoW, structured JSON logging, APScheduler, local filesystem artifact storage

---

### Task 1: Scaffold The Privacy Bounded Context

**Files:**
- Create: `apps/privacy/__init__.py`
- Create: `apps/privacy/domain/__init__.py`
- Create: `apps/privacy/domain/entities.py`
- Create: `apps/privacy/domain/errors.py`
- Create: `apps/privacy/domain/ports/__init__.py`
- Create: `apps/privacy/domain/ports/export_request_repository.py`
- Create: `apps/privacy/domain/ports/export_artifact_storage.py`
- Create: `apps/privacy/domain/ports/subject_data_exporter.py`
- Create: `apps/privacy/application/__init__.py`
- Create: `apps/privacy/interfaces/__init__.py`
- Create: `apps/privacy/infrastructure/__init__.py`
- Verify: none; workspace rule currently forbids adding tests unless explicitly requested

- [ ] **Step 1: Create the export request domain types**

```python
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
    locator: str
    media_type: str
```

- [ ] **Step 2: Create privacy-specific domain errors**

```python
class PrivacyExportNotFoundError(Exception):
    pass


class PrivacyExportNotReadyError(Exception):
    pass


class PrivacyExportAccessDeniedError(Exception):
    pass


class PrivacyExportFailedError(Exception):
    pass


class PrivacyExportExpiredError(Exception):
    pass
```

- [ ] **Step 3: Define the privacy ports**

```python
class ExportRequestRepository(Protocol):
    async def get_by_id(self, request_id: UUID) -> PrivacyExportRequest | None:
        """Return export request by id."""

    async def save(self, request: PrivacyExportRequest) -> None:
        """Persist new or updated export request."""

    async def list_pending(self, *, limit: int) -> list[PrivacyExportRequest]:
        """Return pending export requests, oldest first."""


class ExportArtifactStorage(Protocol):
    async def write_json_bytes(self, *, key: str, payload: bytes) -> PrivacyExportArtifact:
        """Store a JSON artifact and return its metadata."""

    async def open_for_download(self, key: str) -> PrivacyDownloadableArtifact:
        """Resolve a stored artifact for download without leaking storage semantics."""

    async def delete(self, key: str) -> None:
        """Delete an existing artifact if it still exists."""


class SubjectDataExporter(Protocol):
    async def export_for_user(self, user_id: UUID) -> dict[str, object]:
        """Return the bounded-context export payload for one subject."""
```

- [ ] **Step 4: Add package exports for the privacy domain**

```python
from apps.privacy.domain.entities import (
    PrivacyDownloadableArtifact,
    PrivacyExportArtifact,
    PrivacyExportRequest,
    PrivacyExportStatus,
)
```

### Task 2: Add Exporter Ports For Existing Bounded Contexts

**Files:**
- Create: `apps/users/domain/ports/user_data_exporter.py`
- Create: `apps/orders/domain/ports/order_data_exporter.py`
- Create: `apps/organizations/domain/ports/organization_data_exporter.py`
- Create: `apps/users/infrastructure/exporters/user_data_exporter.py`
- Create: `apps/orders/infrastructure/exporters/order_data_exporter.py`
- Create: `apps/organizations/infrastructure/exporters/organization_data_exporter.py`
- Modify: `apps/users/domain/ports/user_repository.py`
- Modify: `apps/orders/domain/ports/order_repository.py`
- Modify: `apps/organizations/domain/ports/organization_repository.py`
- Modify: `apps/organizations/domain/ports/organization_member_repository.py`
- Modify: `apps/organizations/domain/ports/organization_invitation_repository.py`
- Modify: `shipster/platform/persistence/uow.py`

- [ ] **Step 1: Add focused exporter protocols in each bounded context**

```python
class UserDataExporter(Protocol):
    async def export_for_user(self, user_id: UUID) -> dict[str, object]:
        """Return the user-owned users-context export payload."""
```

- [ ] **Step 2: Extend repositories with the minimum query methods needed**

```python
class OrderRepository(Protocol):
    async def list_by_user_id(self, user_id: UUID) -> list[Order]:
        """Return all orders owned by the user."""
```

```python
class OrganizationMemberRepository(Protocol):
    async def list_by_user(self, user_id: UUID) -> list[OrganizationMember]:
        """Return all memberships for the given user."""
```

```python
class OrganizationInvitationRepository(Protocol):
    async def list_by_email(self, email: str) -> list[OrganizationInvitation]:
        """Return invitations addressed to the normalized email."""
```

- [ ] **Step 3: Implement infrastructure exporters that assemble one subdocument each**

```python
class RepositoryUserDataExporter(UserDataExporter):
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def export_for_user(self, user_id: UUID) -> dict[str, object]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
            }
        }
```

```python
class RepositoryOrderDataExporter(OrderDataExporter):
    def __init__(self, *, orders: OrderRepository, users: UserRepository) -> None:
        self._orders = orders
        self._users = users

    async def export_for_user(self, user_id: UUID) -> dict[str, object]:
        if await self._users.get_by_id(user_id) is None:
            raise UserNotFoundError(str(user_id))
        orders = await self._orders.list_by_user_id(user_id)
        return {
            "orders": [
                {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "user_id": None if order.user_id is None else str(order.user_id),
                }
                for order in orders
            ]
        }
```

```python
class RepositoryOrganizationDataExporter(OrganizationDataExporter):
    def __init__(
        self,
        *,
        members: OrganizationMemberRepository,
        invitations: OrganizationInvitationRepository,
        users: UserRepository,
    ) -> None:
        self._members = members
        self._invitations = invitations
        self._users = users

    async def export_for_user(self, user_id: UUID) -> dict[str, object]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        memberships = await self._members.list_by_user(user_id)
        invitations = await self._invitations.list_by_email(user.email)
        return {
            "memberships": [
                {
                    "id": str(member.id),
                    "organization_id": str(member.organization_id),
                    "user_id": str(member.user_id),
                }
                for member in memberships
            ],
            "invitations": [
                {
                    "id": str(invitation.id),
                    "organization_id": str(invitation.organization_id),
                    "email": invitation.email,
                    "status": invitation.status.value,
                    "created_at": invitation.created_at.isoformat(),
                    "expires_at": invitation.expires_at.isoformat(),
                }
                for invitation in invitations
            ],
        }
```

- [ ] **Step 4: Extend the UoW with the new exporter-facing repository access**

```python
class ShipsterUnitOfWork:
    __slots__ = (
        "_orders",
        "_organization_invitations",
        "_organization_members",
        "_organizations",
        "_users",
    )
```

Run: keep the UoW repository properties unchanged, and rely on them to construct privacy exporter adapters in the privacy dependency layer
Expected: no business app imports `shipster`, and privacy orchestration can read users/orders/organizations through existing UoW repositories

### Task 3: Implement Direct Export Application Flow

**Files:**
- Create: `apps/privacy/application/export_document.py`
- Create: `apps/privacy/application/create_data_export.py`
- Create: `apps/privacy/interfaces/api/__init__.py`
- Create: `apps/privacy/interfaces/api/schemas.py`
- Create: `apps/privacy/interfaces/api/privacy_router.py`
- Create: `apps/privacy/interfaces/dependencies.py`
- Modify: `shipster/platform/app.py`

- [ ] **Step 1: Create the export document assembler**

```python
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
```

```python
def write_direct_export_tempfile(payload: bytes, *, suffix: str) -> str:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        handle.write(payload)
        handle.flush()
        return handle.name
    finally:
        handle.close()
```

- [ ] **Step 2: Implement `CreateDataExport` with hybrid decision output**

```python
@dataclass(frozen=True, slots=True)
class DirectDataExportResult:
    filename: str
    media_type: str
    payload: bytes


@dataclass(frozen=True, slots=True)
class AsyncDataExportResult:
    request_id: UUID
    status: str


@dataclass(frozen=True, slots=True)
class DownloadableExport:
    locator: str
    filename: str
    media_type: str
```

```python
class CreateDataExport:
    def __init__(
        self,
        *,
        users_exporter: SubjectDataExporter,
        organizations_exporter: SubjectDataExporter,
        orders_exporter: SubjectDataExporter,
        requests: ExportRequestRepository,
        storage: ExportArtifactStorage,
        direct_export_max_bytes: int,
        expiry_hours: int,
    ) -> None:
        self._users_exporter = users_exporter
        self._organizations_exporter = organizations_exporter
        self._orders_exporter = orders_exporter
        self._requests = requests
        self._storage = storage
        self._direct_export_max_bytes = direct_export_max_bytes
        self._expiry_hours = expiry_hours

    async def execute(self, *, subject_user_id: UUID) -> DirectDataExportResult | AsyncDataExportResult:
        generated_at = datetime.now(UTC)
        users_payload = await self._users_exporter.export_for_user(subject_user_id)
        organizations_payload = await self._organizations_exporter.export_for_user(subject_user_id)
        orders_payload = await self._orders_exporter.export_for_user(subject_user_id)
        document = build_export_document(
            subject_user_id=subject_user_id,
            generated_at=generated_at,
            users_payload=users_payload,
            organizations_payload=organizations_payload,
            orders_payload=orders_payload,
        )
        payload = json.dumps(document, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        if len(payload) <= self._direct_export_max_bytes:
            return DirectDataExportResult(
                filename=f"shipster-export-{subject_user_id}.json",
                media_type="application/json",
                payload=payload,
            )
        request = PrivacyExportRequest(
            id=uuid4(),
            subject_user_id=subject_user_id,
            status=PrivacyExportStatus.PENDING,
            created_at=generated_at,
            updated_at=generated_at,
            expires_at=generated_at + timedelta(hours=self._expiry_hours),
            artifact_key=None,
            failure_reason=None,
        )
        await self._requests.save(request)
        return AsyncDataExportResult(request_id=request.id, status=request.status.value)
```

- [ ] **Step 3: Define privacy API schemas and router endpoints**

```python
class ExportRequestAcceptedResponse(BaseModel):
    request_id: UUID
    status: str


class ExportStatusResponse(BaseModel):
    id: UUID
    status: str
    expires_at: datetime | None


router = APIRouter(prefix="/privacy/exports", tags=["privacy"])


@router.post("")
async def create_export(
    user_id: UUID = Depends(get_current_user_id),
    use_case: CreateDataExport = Depends(get_create_data_export),
):
    result = await use_case.execute(subject_user_id=user_id)
    if isinstance(result, DirectDataExportResult):
        temp_path = write_direct_export_tempfile(result.payload, suffix=".json")
        return FileResponse(path=temp_path, filename=result.filename, media_type=result.media_type)
    return ExportRequestAcceptedResponse(request_id=result.request_id, status=result.status)


@router.get("/{request_id}")
async def get_export_status(
    request_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    use_case: GetDataExportStatus = Depends(get_get_data_export_status),
):
    request = await use_case.execute(request_id=request_id, subject_user_id=user_id)
    return ExportStatusResponse(id=request.id, status=request.status.value, expires_at=request.expires_at)


@router.get("/{request_id}/download")
async def download_export(
    request_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    use_case: DownloadDataExport = Depends(get_download_data_export),
):
    downloadable = await use_case.execute(request_id=request_id, subject_user_id=user_id)
    return FileResponse(
        path=downloadable.locator,
        filename=downloadable.filename,
        media_type=downloadable.media_type,
    )
```

- [ ] **Step 4: Wire current-user auth and router registration**

```python
async def get_create_data_export(
    uow: ShipsterUnitOfWork = Depends(get_uow),
    requests: ExportRequestRepository = Depends(get_export_request_repository),
    storage: ExportArtifactStorage = Depends(get_export_artifact_storage),
) -> CreateDataExport:
    settings = get_global_settings()
    return CreateDataExport(
        users_exporter=RepositoryUserDataExporter(uow.users),
        organizations_exporter=RepositoryOrganizationDataExporter(
            members=uow.organization_members,
            invitations=uow.organization_invitations,
            users=uow.users,
        ),
        orders_exporter=RepositoryOrderDataExporter(orders=uow.orders, users=uow.users),
        requests=requests,
        storage=storage,
        direct_export_max_bytes=settings.privacy_direct_export_max_bytes,
        expiry_hours=settings.privacy_export_expiry_hours,
    )
```

```python
async def get_export_request_repository(
    session: AsyncSession = Depends(get_session),
) -> ExportRequestRepository:
    return SqlAlchemyExportRequestRepository(session)


async def get_export_artifact_storage() -> ExportArtifactStorage:
    settings = get_global_settings()
    return LocalExportArtifactStorage(Path(settings.privacy_export_dir))


async def get_get_data_export_status(
    requests: ExportRequestRepository = Depends(get_export_request_repository),
) -> GetDataExportStatus:
    return GetDataExportStatus(requests=requests)


async def get_download_data_export(
    requests: ExportRequestRepository = Depends(get_export_request_repository),
    storage: ExportArtifactStorage = Depends(get_export_artifact_storage),
) -> DownloadDataExport:
    return DownloadDataExport(requests=requests, storage=storage)
```

Run: import and register `privacy_router` in `shipster/platform/app.py`
Expected: privacy endpoints appear alongside auth/users/orders/organizations

### Task 4: Add Async Export Persistence And Artifact Storage

**Files:**
- Create: `apps/privacy/infrastructure/persistence/__init__.py`
- Create: `apps/privacy/infrastructure/persistence/schema/__init__.py`
- Create: `apps/privacy/infrastructure/persistence/schema/privacy_export_request.py`
- Create: `apps/privacy/infrastructure/persistence/repository/export_request.py`
- Create: `apps/privacy/infrastructure/storage/__init__.py`
- Create: `apps/privacy/infrastructure/storage/local_export_artifact_storage.py`
- Modify: `shipster/platform/persistence/database.py`
- Modify: `shipster/platform/settings.py`

- [ ] **Step 1: Create the ORM model for export requests**

```python
class PrivacyExportRequestORM(Base):
    __tablename__ = "privacy_export_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subject_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    artifact_key: Mapped[str | None]
    failure_reason: Mapped[str | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    expires_at: Mapped[datetime | None]
```

- [ ] **Step 2: Implement the SQLAlchemy repository**

```python
class SqlAlchemyExportRequestRepository(ExportRequestRepository):
    async def get_by_id(self, request_id: UUID) -> PrivacyExportRequest | None:
        row = await self._session.get(PrivacyExportRequestORM, str(request_id))
        return None if row is None else map_privacy_export_request(row)

    async def list_pending(self, *, limit: int) -> list[PrivacyExportRequest]:
        stmt = (
            select(PrivacyExportRequestORM)
            .where(PrivacyExportRequestORM.status == PrivacyExportStatus.PENDING.value)
            .order_by(PrivacyExportRequestORM.created_at.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [map_privacy_export_request(row) for row in rows]

    async def save(self, request: PrivacyExportRequest) -> None:
        existing = await self._session.get(PrivacyExportRequestORM, str(request.id))
        if existing is None:
            self._session.add(map_privacy_export_request_to_orm(request))
            await self._session.flush()
            return
        existing.status = request.status.value
        existing.updated_at = request.updated_at
        existing.expires_at = request.expires_at
        existing.artifact_key = request.artifact_key
        existing.failure_reason = request.failure_reason
        await self._session.flush()
```

```python
def map_privacy_export_request(row: PrivacyExportRequestORM) -> PrivacyExportRequest:
    return PrivacyExportRequest(
        id=UUID(row.id),
        subject_user_id=UUID(row.subject_user_id),
        status=PrivacyExportStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        expires_at=row.expires_at,
        artifact_key=row.artifact_key,
        failure_reason=row.failure_reason,
    )


def map_privacy_export_request_to_orm(request: PrivacyExportRequest) -> PrivacyExportRequestORM:
    return PrivacyExportRequestORM(
        id=str(request.id),
        subject_user_id=str(request.subject_user_id),
        status=request.status.value,
        created_at=request.created_at,
        updated_at=request.updated_at,
        expires_at=request.expires_at,
        artifact_key=request.artifact_key,
        failure_reason=request.failure_reason,
    )
```

- [ ] **Step 3: Implement local artifact storage behind a port**

```python
class LocalExportArtifactStorage(ExportArtifactStorage):
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    async def write_json_bytes(self, *, key: str, payload: bytes) -> PrivacyExportArtifact:
        path = self._base_dir / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return PrivacyExportArtifact(
            key=key,
            filename=f"{key}.json",
            media_type="application/json",
            size_bytes=len(payload),
        )
```

- [ ] **Step 4: Register ORM metadata and storage settings**

```python
privacy_export_dir: str = Field(default=".shipster_privacy_exports")
privacy_export_expiry_hours: int = Field(default=24)
privacy_direct_export_max_bytes: int = Field(default=262144)
```

Run: import `PrivacyExportRequestORM` inside `_register_orm_metadata()` in `shipster/platform/persistence/database.py`
Expected: metadata is complete before `create_all`

### Task 5: Implement Async Processing, Status, And Download

**Files:**
- Create: `apps/privacy/application/get_data_export_status.py`
- Create: `apps/privacy/application/download_data_export.py`
- Create: `apps/privacy/application/process_pending_exports.py`
- Create: `apps/privacy/interfaces/schedule_registration.py`
- Modify: `shipster/platform/scheduler/bootstrap.py`
- Modify: `apps/privacy/interfaces/dependencies.py`
- Modify: `apps/privacy/interfaces/api/privacy_router.py`

- [ ] **Step 1: Implement status and download use cases**

```python
class GetDataExportStatus:
    async def execute(self, *, request_id: UUID, subject_user_id: UUID) -> PrivacyExportRequest:
        request = await self._requests.get_by_id(request_id)
        if request is None:
            raise PrivacyExportNotFoundError()
        if request.subject_user_id != subject_user_id:
            raise PrivacyExportAccessDeniedError()
        return request


class DownloadDataExport:
    async def execute(self, *, request_id: UUID, subject_user_id: UUID) -> DownloadableExport:
        request = await self._requests.get_by_id(request_id)
        if request is None:
            raise PrivacyExportNotFoundError()
        if request.subject_user_id != subject_user_id:
            raise PrivacyExportAccessDeniedError()
        if request.status == PrivacyExportStatus.EXPIRED:
            raise PrivacyExportExpiredError()
        if request.status == PrivacyExportStatus.FAILED:
            raise PrivacyExportFailedError()
        if request.status != PrivacyExportStatus.READY or request.artifact_key is None:
            raise PrivacyExportNotReadyError()
        artifact = await self._storage.open_for_download(request.artifact_key)
        return DownloadableExport(
            locator=artifact.locator,
            filename=f"shipster-export-{request.id}.json",
            media_type=artifact.media_type,
        )
```

- [ ] **Step 2: Implement pending export processing**

```python
class ProcessPendingExports:
    async def execute(self, *, limit: int = 10) -> None:
        pending = await self._requests.list_pending(limit=limit)
        for request in pending:
            started_at = datetime.now(UTC)
            processing = PrivacyExportRequest(
                id=request.id,
                subject_user_id=request.subject_user_id,
                status=PrivacyExportStatus.PROCESSING,
                created_at=request.created_at,
                updated_at=started_at,
                expires_at=request.expires_at,
                artifact_key=None,
                failure_reason=None,
            )
            await self._requests.save(processing)
            try:
                payload = await self._builder.build_bytes(subject_user_id=request.subject_user_id)
                artifact = await self._storage.write_json_bytes(key=str(request.id), payload=payload)
                ready = PrivacyExportRequest(
                    id=request.id,
                    subject_user_id=request.subject_user_id,
                    status=PrivacyExportStatus.READY,
                    created_at=request.created_at,
                    updated_at=datetime.now(UTC),
                    expires_at=request.expires_at,
                    artifact_key=artifact.key,
                    failure_reason=None,
                )
                await self._requests.save(ready)
            except Exception as exc:
                failed = PrivacyExportRequest(
                    id=request.id,
                    subject_user_id=request.subject_user_id,
                    status=PrivacyExportStatus.FAILED,
                    created_at=request.created_at,
                    updated_at=datetime.now(UTC),
                    expires_at=request.expires_at,
                    artifact_key=None,
                    failure_reason=str(exc),
                )
                await self._requests.save(failed)
```

- [ ] **Step 3: Register a privacy scheduler job**

```python
def register(registry: ScheduleRegistry) -> None:
    registry.add_interval_job(
        "privacy.process_pending_exports",
        seconds=30.0,
        func=run_privacy_pending_export_poll,
    )
```

```python
async def run_privacy_pending_export_poll() -> None:
    processor = ensure_process_pending_exports()
    await processor.execute(limit=10)
```

- [ ] **Step 4: Return correct FastAPI responses**

```python
return FileResponse(path=path, filename=filename, media_type=media_type)
```

Run: use `get_current_user_id` in the privacy router and map privacy errors to `404`, `409`, `410`, or `500` as appropriate
Expected: direct exports download immediately, async exports expose status then download when ready

### Task 6: Verification

**Files:**
- Verify: `apps/privacy/`
- Verify: `shipster/platform/app.py`
- Verify: `shipster/platform/persistence/database.py`
- Verify: `shipster/platform/persistence/uow.py`
- Verify: `shipster/platform/settings.py`
- Verify: `shipster/platform/scheduler/bootstrap.py`

- [ ] **Step 1: Format the Python code**

Run: `ruff format shipster apps`
Expected: files are formatted or already clean

- [ ] **Step 2: Lint the Python code**

Run: `ruff check shipster apps`
Expected: exit 0

- [ ] **Step 3: Verify Python syntax/importability**

Run: `python3 -m compileall shipster apps`
Expected: exit 0

- [ ] **Step 4: Verify import architecture contracts**

Run: `.venv/bin/lint-imports`
Expected: exit 0

### Task 7: Workspace Rule Note

**Files:**
- Review: `docs/superpowers/specs/2026-04-10-gdpr-data-export-design.md`

- [ ] **Step 1: Preserve the workspace testing policy**

Run: implement the plan without creating or editing test files unless the user explicitly asks for tests
Expected: the feature remains structured around ports/use cases so tests can be added later without redesign
