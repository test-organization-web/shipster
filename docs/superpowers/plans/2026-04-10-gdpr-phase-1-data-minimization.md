# GDPR Phase 1 Data Minimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce unnecessary exposure of personal data and secrets in logs and message handling without changing the existing invitation delivery behavior.

**Architecture:** Keep privacy controls close to the cross-cutting infrastructure that emits data today. Apply HTTP audit minimization in `shipster.platform`, keep invitation-specific minimization in `apps.organizations`, and avoid introducing a new bounded context until the first high-risk leaks are closed.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, structured JSON logging, Redis/RabbitMQ-backed messaging

---

### Task 1: Minimize HTTP Audit Logging

**Files:**
- Modify: `shipster/platform/http_audit.py`
- Modify: `shipster/platform/settings.py`

- [ ] **Step 1: Add a settings-controlled body logging flag**

```python
http_audit_log_bodies: bool = Field(
    default=False,
    description="If true, include redacted request/response body previews in shipster.audit.http logs.",
)
```

- [ ] **Step 2: Wire the setting from environment**

Run: update `get_global_settings()` to read `SHIPSTER_HTTP_AUDIT_LOG_BODIES` with `_env_bool_default(..., False)`
Expected: body previews are disabled by default

- [ ] **Step 3: Remove default body capture from the audit payload**

```python
extra = {
    "event": "http_audit",
    "http_method": scope.get("method"),
    "path": scope.get("path"),
    "path_params": path_params,
    "status_code": status_code,
    "duration_s": round(duration_s, 4),
}
if settings.http_audit_log_bodies:
    extra["request_body"] = ...
    extra["response_body"] = ...
```

- [ ] **Step 4: Drop raw client IP from default audit payload**

```python
# Do not log client_addr by default; IP addresses are personal data.
```

- [ ] **Step 5: Keep query logging sanitized and bounded**

Run: keep query parameters only after redaction/sanitization
Expected: token/password-style keys remain redacted when present

### Task 2: Sanitize Structured Application Logs

**Files:**
- Modify: `shipster/platform/logging_bootstrap.py`

- [ ] **Step 1: Add top-level sensitive key redaction**

```python
_SENSITIVE_LOG_KEYS = frozenset(
    {"access_token", "authorization", "password", "refresh_token", "token", "email"}
)
```

- [ ] **Step 2: Redact mappings recursively**

```python
def _sanitize_mapping(mapping: Mapping[object, object]) -> dict[str, object]:
    sanitized: dict[str, object] = {}
    for key, value in mapping.items():
        key_text = str(key)
        if key_text.lower() in _SENSITIVE_LOG_KEYS:
            sanitized[key_text] = "***REDACTED***"
        else:
            sanitized[key_text] = _coerce_json(value)
    return sanitized
```

- [ ] **Step 3: Apply redaction to formatter extras**

Run: update `JsonLogFormatter.format()` so extra fields with sensitive names are redacted before serialization
Expected: existing `extra={"email": ...}` logs no longer emit raw emails

### Task 3: Reduce Invitation Flow Exposure

**Files:**
- Modify: `apps/organizations/application/invite_organization_member.py`
- Modify: `apps/organizations/application/messaging/organization_invitation_created_handler.py`

- [ ] **Step 1: Remove raw email from invitation logs**

```python
extra={
    "event": "organization_invitation_created",
    "invitation_id": invitation.id,
    "organization_id": invitation.organization_id,
    "invited_by_user_id": invitation.invited_by_user_id,
    "expires_at": invitation.expires_at,
}
```

- [ ] **Step 2: Remove noisy non-essential handler log**

```python
# Delete: logger.info("test send invitation")
```

- [ ] **Step 3: Redact raw email in failure logs**

Run: remove `email` from publish failure extras
Expected: invitation failures remain diagnosable without exposing recipient PII

### Task 4: Verify the Slice

**Files:**
- Verify: `shipster/platform/http_audit.py`
- Verify: `shipster/platform/settings.py`
- Verify: `shipster/platform/logging_bootstrap.py`
- Verify: `apps/organizations/application/invite_organization_member.py`
- Verify: `apps/organizations/application/messaging/organization_invitation_created_handler.py`

- [ ] **Step 1: Run import-linter**

Run: `lint-imports`
Expected: exit 0

- [ ] **Step 2: Run Ruff lint**

Run: `ruff check app apps tests alembic`
Expected: exit 0

- [ ] **Step 3: Run Ruff format**

Run: `ruff format app apps tests alembic`
Expected: files are formatted or already clean

- [ ] **Step 4: Run focused syntax check if project paths differ**

Run: `python -m compileall shipster apps`
Expected: exit 0
