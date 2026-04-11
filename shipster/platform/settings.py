"""Process-wide application settings (environment-driven composition root)."""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATABASE_URL = "sqlite+pysqlite:///:memory:"
_DEFAULT_REDIS_URL = "redis://localhost:6379/0"
_DEFAULT_MESSAGING_BACKEND = "redis"
_DEFAULT_RABBITMQ_URL: str | None = None
_DEFAULT_SMTP_HOST = "localhost"
_DEFAULT_SMTP_PORT = 25
_DEFAULT_SMTP_USERNAME: str | None = None
_DEFAULT_SMTP_PASSWORD: str | None = None
_DEFAULT_SMTP_USE_TLS = False
_DEFAULT_SMTP_START_TLS = True
_DEFAULT_SMTP_TIMEOUT_SECONDS = 60.0
_DEFAULT_SMTP_DEFAULT_FROM_EMAIL = "noreply@localhost"
_DEFAULT_SMTP_DEFAULT_FROM_NAME: str | None = "Shipster"
_DEFAULT_TELEGRAM_BOT_TOKEN: str | None = None
_DEFAULT_TELEGRAM_BASE_URL = "https://api.telegram.org"
_DEFAULT_TELEGRAM_TIMEOUT_SECONDS = 10.0
_DEFAULT_ORG_INVITATION_ACCEPT_URL_TEMPLATE: str | None = None
# HS256 needs a >=32-byte key (RFC 7518); old 29-char default triggered PyJWT warnings.
_DEFAULT_JWT_SECRET = "dev-insecure-secret-change-me-32b"
_DEFAULT_LOG_LEVEL = "INFO"
_DEFAULT_JSON_LOGS = True
_DEFAULT_ACCESS_LOG = True
_DEFAULT_PRIVACY_EXPORT_ARTIFACT_DIR = str(_PROJECT_ROOT / ".shipster_privacy_exports")
_DEFAULT_PRIVACY_EXPORT_EXPIRY_HOURS = 24
_DEFAULT_PRIVACY_DIRECT_EXPORT_MAX_BYTES = 262_144
_DEFAULT_PRIVACY_PENDING_EXPORT_POLL_SECONDS = 30.0
_DEFAULT_PRIVACY_PENDING_ERASURE_POLL_SECONDS = 30.0


class GlobalSettings(BaseModel):
    """Runtime configuration for Shipster (see :func:`get_global_settings`)."""

    model_config = {"frozen": True}

    database_url: str = Field(default=_DEFAULT_DATABASE_URL)
    redis_url: str = Field(default=_DEFAULT_REDIS_URL)
    messaging_backend: str = Field(default=_DEFAULT_MESSAGING_BACKEND)
    rabbitmq_url: str | None = Field(default=_DEFAULT_RABBITMQ_URL)
    smtp_host: str = Field(default=_DEFAULT_SMTP_HOST)
    smtp_port: int = Field(default=_DEFAULT_SMTP_PORT)
    smtp_username: str | None = Field(default=_DEFAULT_SMTP_USERNAME)
    smtp_password: str | None = Field(default=_DEFAULT_SMTP_PASSWORD)
    smtp_use_tls: bool = Field(default=_DEFAULT_SMTP_USE_TLS)
    smtp_start_tls: bool = Field(default=_DEFAULT_SMTP_START_TLS)
    smtp_timeout_seconds: float = Field(default=_DEFAULT_SMTP_TIMEOUT_SECONDS)
    smtp_default_from_email: str = Field(default=_DEFAULT_SMTP_DEFAULT_FROM_EMAIL)
    smtp_default_from_name: str | None = Field(default=_DEFAULT_SMTP_DEFAULT_FROM_NAME)
    telegram_bot_token: str | None = Field(default=_DEFAULT_TELEGRAM_BOT_TOKEN)
    telegram_base_url: str = Field(default=_DEFAULT_TELEGRAM_BASE_URL)
    telegram_timeout_seconds: float = Field(default=_DEFAULT_TELEGRAM_TIMEOUT_SECONDS)
    jwt_secret: str = Field(default=_DEFAULT_JWT_SECRET)
    log_level: str = Field(default=_DEFAULT_LOG_LEVEL)
    json_logs: bool = Field(default=_DEFAULT_JSON_LOGS)
    access_log: bool = Field(default=_DEFAULT_ACCESS_LOG)
    background_jobs_enabled: bool = Field(
        default=True,
        description="Enable scheduler/background jobs in the current process.",
    )
    organization_invitation_accept_url_template: str | None = Field(
        default=_DEFAULT_ORG_INVITATION_ACCEPT_URL_TEMPLATE,
        description="Optional URL template using {token} and optionally {organization_id}.",
    )
    debug_request_timing: bool = Field(
        default=False,
        description="Enables DEBUG on shipster.debug.request_timing (latency split logs).",
    )
    http_audit_enabled: bool = Field(
        default=False,
        description=(
            "Enables INFO HTTP audit logs (request/response preview, duration) "
            "on shipster.audit.http."
        ),
    )
    http_audit_log_bodies: bool = Field(
        default=False,
        description=(
            "If true, include redacted request/response body previews in shipster.audit.http logs."
        ),
    )
    privacy_export_artifact_dir: str = Field(default=_DEFAULT_PRIVACY_EXPORT_ARTIFACT_DIR)
    privacy_export_expiry_hours: int = Field(default=_DEFAULT_PRIVACY_EXPORT_EXPIRY_HOURS)
    privacy_direct_export_max_bytes: int = Field(
        default=_DEFAULT_PRIVACY_DIRECT_EXPORT_MAX_BYTES,
    )
    privacy_pending_export_poll_seconds: float = Field(
        default=_DEFAULT_PRIVACY_PENDING_EXPORT_POLL_SECONDS,
    )
    privacy_pending_erasure_poll_seconds: float = Field(
        default=_DEFAULT_PRIVACY_PENDING_ERASURE_POLL_SECONDS,
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: object) -> str:
        normalized = str(value or _DEFAULT_LOG_LEVEL).strip().upper()
        if normalized in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            return normalized
        return _DEFAULT_LOG_LEVEL


def _first_env(*names: str) -> str | None:
    for name in names:
        v = os.environ.get(name)
        if v is not None and v != "":
            return v
    return None


def _env_bool_default(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return str(raw).lower().strip() in ("1", "true", "yes")


def _resolve_privacy_export_artifact_dir(path_value: str) -> str:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    return str(path.resolve())


@lru_cache(maxsize=1)
def get_global_settings() -> GlobalSettings:
    """Return cached settings (one instance per process)."""
    return GlobalSettings(
        database_url=_first_env("SHIPSTER_DATABASE_URL", "DATABASE_URL") or _DEFAULT_DATABASE_URL,
        redis_url=_first_env("REDIS_URL", "SHIPSTER_REDIS_URL") or _DEFAULT_REDIS_URL,
        messaging_backend=_first_env("MESSAGING_BACKEND", "SHIPSTER_MESSAGING_BACKEND")
        or _DEFAULT_MESSAGING_BACKEND,
        rabbitmq_url=_first_env("SHIPSTER_RABBITMQ_URL", "RABBITMQ_URL"),
        smtp_host=_first_env("SHIPSTER_SMTP_HOST", "SMTP_HOST") or _DEFAULT_SMTP_HOST,
        smtp_port=int(
            _first_env("SHIPSTER_SMTP_PORT", "SMTP_PORT") or _DEFAULT_SMTP_PORT,
        ),
        smtp_username=_first_env("SHIPSTER_SMTP_USERNAME", "SMTP_USERNAME"),
        smtp_password=_first_env("SHIPSTER_SMTP_PASSWORD", "SMTP_PASSWORD"),
        smtp_use_tls=_env_bool_default("SHIPSTER_SMTP_USE_TLS", _DEFAULT_SMTP_USE_TLS),
        smtp_start_tls=_env_bool_default("SHIPSTER_SMTP_START_TLS", _DEFAULT_SMTP_START_TLS),
        smtp_timeout_seconds=float(
            _first_env("SHIPSTER_SMTP_TIMEOUT_SECONDS", "SMTP_TIMEOUT_SECONDS")
            or _DEFAULT_SMTP_TIMEOUT_SECONDS,
        ),
        smtp_default_from_email=(
            _first_env("SHIPSTER_SMTP_DEFAULT_FROM_EMAIL", "SMTP_DEFAULT_FROM_EMAIL")
            or _DEFAULT_SMTP_DEFAULT_FROM_EMAIL
        ),
        smtp_default_from_name=(
            _first_env("SHIPSTER_SMTP_DEFAULT_FROM_NAME", "SMTP_DEFAULT_FROM_NAME")
            or _DEFAULT_SMTP_DEFAULT_FROM_NAME
        ),
        telegram_bot_token=_first_env("SHIPSTER_TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN"),
        telegram_base_url=(
            _first_env("SHIPSTER_TELEGRAM_BASE_URL", "TELEGRAM_BASE_URL")
            or _DEFAULT_TELEGRAM_BASE_URL
        ),
        telegram_timeout_seconds=float(
            _first_env("SHIPSTER_TELEGRAM_TIMEOUT_SECONDS", "TELEGRAM_TIMEOUT_SECONDS")
            or _DEFAULT_TELEGRAM_TIMEOUT_SECONDS,
        ),
        jwt_secret=os.environ.get("SHIPSTER_JWT_SECRET") or _DEFAULT_JWT_SECRET,
        log_level=os.environ.get("SHIPSTER_LOG_LEVEL") or _DEFAULT_LOG_LEVEL,
        json_logs=_env_bool_default("SHIPSTER_JSON_LOGS", _DEFAULT_JSON_LOGS),
        access_log=_env_bool_default("SHIPSTER_ACCESS_LOG", _DEFAULT_ACCESS_LOG),
        background_jobs_enabled=_env_bool_default("SHIPSTER_BACKGROUND_JOBS_ENABLED", True),
        organization_invitation_accept_url_template=_first_env(
            "SHIPSTER_ORG_INVITATION_ACCEPT_URL_TEMPLATE",
            "ORG_INVITATION_ACCEPT_URL_TEMPLATE",
        ),
        debug_request_timing=_env_bool_default("SHIPSTER_DEBUG_REQUEST_TIMING", False),
        http_audit_enabled=_env_bool_default("SHIPSTER_HTTP_AUDIT", False),
        http_audit_log_bodies=_env_bool_default("SHIPSTER_HTTP_AUDIT_LOG_BODIES", False),
        privacy_export_artifact_dir=(
            _resolve_privacy_export_artifact_dir(
                _first_env(
                    "SHIPSTER_PRIVACY_EXPORT_ARTIFACT_DIR",
                    "PRIVACY_EXPORT_ARTIFACT_DIR",
                )
                or _DEFAULT_PRIVACY_EXPORT_ARTIFACT_DIR,
            )
        ),
        privacy_export_expiry_hours=int(
            _first_env(
                "SHIPSTER_PRIVACY_EXPORT_EXPIRY_HOURS",
                "PRIVACY_EXPORT_EXPIRY_HOURS",
            )
            or _DEFAULT_PRIVACY_EXPORT_EXPIRY_HOURS,
        ),
        privacy_direct_export_max_bytes=int(
            _first_env(
                "SHIPSTER_PRIVACY_DIRECT_EXPORT_MAX_BYTES",
                "PRIVACY_DIRECT_EXPORT_MAX_BYTES",
            )
            or _DEFAULT_PRIVACY_DIRECT_EXPORT_MAX_BYTES,
        ),
        privacy_pending_export_poll_seconds=float(
            _first_env(
                "SHIPSTER_PRIVACY_PENDING_EXPORT_POLL_SECONDS",
                "PRIVACY_PENDING_EXPORT_POLL_SECONDS",
            )
            or _DEFAULT_PRIVACY_PENDING_EXPORT_POLL_SECONDS,
        ),
        privacy_pending_erasure_poll_seconds=float(
            _first_env(
                "SHIPSTER_PRIVACY_PENDING_ERASURE_POLL_SECONDS",
                "PRIVACY_PENDING_ERASURE_POLL_SECONDS",
            )
            or _DEFAULT_PRIVACY_PENDING_ERASURE_POLL_SECONDS,
        ),
    )
