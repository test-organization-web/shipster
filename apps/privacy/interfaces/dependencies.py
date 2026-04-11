from functools import lru_cache
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.orders.infrastructure.erasers.order_subject_data_eraser import OrderSubjectDataEraser
from apps.orders.infrastructure.exporters.order_data_exporter import RepositoryOrderDataExporter
from apps.organizations.infrastructure.erasers.organization_invitations_subject_data_eraser import (
    OrganizationInvitationsSubjectDataEraser,
)
from apps.organizations.infrastructure.exporters.organization_data_exporter import (
    RepositoryOrganizationDataExporter,
)
from apps.privacy.application.create_data_export import CreateDataExport
from apps.privacy.application.download_data_export import DownloadDataExport
from apps.privacy.application.get_data_export_status import GetDataExportStatus
from apps.privacy.application.get_erasure_status import GetErasureStatus
from apps.privacy.application.list_export_lifecycle_events import ListExportLifecycleEvents
from apps.privacy.application.process_pending_erasure_requests import ProcessPendingErasureRequests
from apps.privacy.application.process_pending_exports import ProcessPendingExports
from apps.privacy.application.request_erasure import RequestErasure
from apps.privacy.domain.ports.erasure_request_repository import ErasureRequestRepository
from apps.privacy.domain.ports.export_artifact_storage import ExportArtifactStorage
from apps.privacy.domain.ports.export_request_repository import ExportRequestRepository
from apps.privacy.infrastructure.direct_export_eligibility import (
    RepositoryDirectExportEligibilityProbe,
)
from apps.privacy.infrastructure.erasers.privacy_exports_subject_data_eraser import (
    PrivacyExportsSubjectDataEraser,
)
from apps.privacy.infrastructure.persistence.repository.erasure_request import (
    SqlAlchemyErasureRequestRepository,
)
from apps.privacy.infrastructure.persistence.repository.export_request import (
    SqlAlchemyExportRequestRepository,
)
from apps.privacy.infrastructure.storage.local_export_artifact_storage import (
    LocalExportArtifactStorage,
)
from apps.users.infrastructure.erasers.user_subject_data_eraser import UserSubjectDataEraser
from apps.users.infrastructure.exporters.user_data_exporter import RepositoryUserDataExporter
from apps.users.infrastructure.security.pbkdf2_password_hasher import Pbkdf2PasswordHasher
from shipster.platform.persistence import ShipsterUnitOfWork, get_session, get_uow
from shipster.platform.settings import GlobalSettings, get_global_settings


@lru_cache(maxsize=1)
def _artifact_storage(base_dir: str) -> LocalExportArtifactStorage:
    return LocalExportArtifactStorage(Path(base_dir))


@lru_cache(maxsize=1)
def _pbkdf2_password_hasher() -> Pbkdf2PasswordHasher:
    return Pbkdf2PasswordHasher()


def _settings() -> GlobalSettings:
    return get_global_settings()


def build_process_pending_exports(
    *,
    session: AsyncSession,
    uow: ShipsterUnitOfWork,
    settings: GlobalSettings,
) -> ProcessPendingExports:
    return ProcessPendingExports(
        users_exporter=RepositoryUserDataExporter(uow.users),
        organizations_exporter=RepositoryOrganizationDataExporter(
            members=uow.organization_members,
            invitations=uow.organization_invitations,
            users=uow.users,
        ),
        orders_exporter=RepositoryOrderDataExporter(orders=uow.orders, users=uow.users),
        requests=SqlAlchemyExportRequestRepository(session),
        storage=_artifact_storage(settings.privacy_export_artifact_dir),
        expiry_hours=settings.privacy_export_expiry_hours,
    )


def build_process_pending_erasure_requests(
    *,
    session: AsyncSession,
    uow: ShipsterUnitOfWork,
    settings: GlobalSettings,
) -> ProcessPendingErasureRequests:
    export_repo = SqlAlchemyExportRequestRepository(session)
    return ProcessPendingErasureRequests(
        erasures=SqlAlchemyErasureRequestRepository(session),
        privacy_eraser=PrivacyExportsSubjectDataEraser(
            export_requests=export_repo,
            storage=_artifact_storage(settings.privacy_export_artifact_dir),
        ),
        organizations_eraser=OrganizationInvitationsSubjectDataEraser(
            users=uow.users,
            invitations=uow.organization_invitations,
        ),
        users_eraser=UserSubjectDataEraser(
            users=uow.users,
            password_hasher=_pbkdf2_password_hasher(),
        ),
        orders_eraser=OrderSubjectDataEraser(),
    )


async def get_export_request_repository(
    session: AsyncSession = Depends(get_session),
) -> ExportRequestRepository:
    return SqlAlchemyExportRequestRepository(session)


async def get_erasure_request_repository(
    session: AsyncSession = Depends(get_session),
) -> ErasureRequestRepository:
    return SqlAlchemyErasureRequestRepository(session)


async def get_export_artifact_storage() -> ExportArtifactStorage:
    settings = _settings()
    return _artifact_storage(settings.privacy_export_artifact_dir)


async def get_create_data_export(
    uow: ShipsterUnitOfWork = Depends(get_uow),
    requests: ExportRequestRepository = Depends(get_export_request_repository),
    storage: ExportArtifactStorage = Depends(get_export_artifact_storage),
) -> CreateDataExport:
    settings = _settings()
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
        direct_export_probe=RepositoryDirectExportEligibilityProbe(
            users=uow.users,
            members=uow.organization_members,
            invitations=uow.organization_invitations,
            orders=uow.orders,
            direct_export_max_bytes=settings.privacy_direct_export_max_bytes,
        ),
        direct_export_max_bytes=settings.privacy_direct_export_max_bytes,
        export_expiry_hours=settings.privacy_export_expiry_hours,
    )


async def get_get_data_export_status(
    requests: ExportRequestRepository = Depends(get_export_request_repository),
    storage: ExportArtifactStorage = Depends(get_export_artifact_storage),
) -> GetDataExportStatus:
    return GetDataExportStatus(requests=requests, storage=storage)


async def get_download_data_export(
    requests: ExportRequestRepository = Depends(get_export_request_repository),
    storage: ExportArtifactStorage = Depends(get_export_artifact_storage),
) -> DownloadDataExport:
    return DownloadDataExport(requests=requests, storage=storage)


async def get_list_export_lifecycle_events(
    requests: ExportRequestRepository = Depends(get_export_request_repository),
    storage: ExportArtifactStorage = Depends(get_export_artifact_storage),
) -> ListExportLifecycleEvents:
    return ListExportLifecycleEvents(
        get_export_status=GetDataExportStatus(requests=requests, storage=storage),
        requests=requests,
    )


async def get_request_erasure(
    uow: ShipsterUnitOfWork = Depends(get_uow),
    erasures: ErasureRequestRepository = Depends(get_erasure_request_repository),
) -> RequestErasure:
    return RequestErasure(users=uow.users, erasures=erasures)


async def get_get_erasure_status(
    erasures: ErasureRequestRepository = Depends(get_erasure_request_repository),
) -> GetErasureStatus:
    return GetErasureStatus(erasures=erasures)
