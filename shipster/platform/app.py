"""FastAPI application factory and router registration."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.auth.interfaces.api import auth_router
from apps.orders.interfaces.api import order_router
from apps.organizations.interfaces.api import organization_router
from apps.privacy.interfaces.api import privacy_erasure_router, privacy_router
from apps.users.interfaces.api import user_router
from shipster.platform.http_audit import HttpAuditMiddleware
from shipster.platform.logging_bootstrap import (
    configure_application_logging,
    configure_http_audit_logging,
    configure_request_timing_logging,
)
from shipster.platform.persistence.database import init_async_database
from shipster.platform.redis_client import close_async_redis
from shipster.platform.settings import get_global_settings

_LOG = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    _LOG.info("Shipster startup beginning", extra={"event": "app_startup_begin"})
    try:
        await init_async_database()
        _LOG.info("Database initialized", extra={"event": "database_initialized"})
        await configure_request_timing_logging()
        await configure_http_audit_logging()
        _LOG.info("Shipster startup complete", extra={"event": "app_startup_complete"})
        yield
    finally:
        _LOG.info("Shipster shutdown beginning", extra={"event": "app_shutdown_begin"})
        await close_async_redis()
        _LOG.info("Shipster shutdown complete", extra={"event": "app_shutdown_complete"})


def create_app() -> FastAPI:
    configure_application_logging()
    settings = get_global_settings()
    app = FastAPI(title="Shipster", lifespan=_lifespan)
    if settings.http_audit_enabled:
        app.add_middleware(HttpAuditMiddleware)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(order_router)
    app.include_router(organization_router)
    app.include_router(privacy_router)
    app.include_router(privacy_erasure_router)
    return app
