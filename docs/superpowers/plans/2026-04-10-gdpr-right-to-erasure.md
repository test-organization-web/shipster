# GDPR Right to Erasure (v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Subject-initiated **right to erasure v1**: durable **`privacy_erasure_requests`**, **async processing** via scheduler, **anonymize + deactivate** the `users` row (per approved spec), scrub **organization invitations** addressed to the user’s email, and **clean up privacy export artifacts/requests** for that subject.

**Architecture:** `apps/privacy` owns erasure request persistence + orchestration + HTTP. Each bounded context exposes a small `SubjectDataEraser` port (defined under `apps/privacy/domain/ports/`) implemented in that context’s `infrastructure/erasers/`. Processing runs in a dedicated privacy use case using **one `AsyncSession` per poll** (same pattern as export polling).

**Tech stack:** FastAPI, SQLAlchemy async, existing scheduler registry.

**Spec (approved):** `docs/superpowers/specs/2026-04-10-gdpr-right-to-erasure-design.md`

**Testing policy (Shipster workspace):** Do **not** add/expand `tests/` unless the user explicitly asks. Verify with **manual checks** + `ruff` + `lint-imports` + `compileall`.

**User strategy (approved):** **Anonymize + deactivate** (keep `users.id`).

---

## File map

**Create (privacy)**

- `apps/privacy/domain/ports/subject_data_eraser.py` — `SubjectDataEraser` Protocol
- `apps/privacy/domain/entities.py` — extend with erasure types **or** new `apps/privacy/domain/erasure_entities.py` (pick one; keep imports tidy)
- `apps/privacy/domain/errors.py` — erasure-specific errors (not found, denied, conflict, subject missing)
- `apps/privacy/domain/ports/erasure_request_repository.py` — `ErasureRequestRepository` Protocol
- `apps/privacy/infrastructure/persistence/schema/privacy_erasure_request.py` — `PrivacyErasureRequestORM`
- `apps/privacy/infrastructure/persistence/repository/erasure_request.py` — SQLAlchemy repo
- `apps/privacy/application/request_erasure.py`
- `apps/privacy/application/get_erasure_status.py`
- `apps/privacy/application/process_pending_erasure_requests.py`
- `apps/privacy/interfaces/api/privacy_erasure_router.py`
- `apps/privacy/interfaces/api/erasure_schemas.py` (or extend `schemas.py` if you prefer fewer files)

**Create (per-context erasers)**

- `apps/users/infrastructure/erasers/user_subject_data_eraser.py`
- `apps/organizations/infrastructure/erasers/organization_subject_data_eraser.py`
- `apps/orders/infrastructure/erasers/order_subject_data_eraser.py` — **no-op** `erase_for_user` (document why: no PII columns beyond nullable `user_id` today)

**Modify**

- `apps/privacy/domain/ports/export_request_repository.py` + `apps/privacy/infrastructure/persistence/repository/export_request.py` — add `list_all_for_subject_user(subject_user_id)` (name flexible) used only for export cleanup during erasure
- `apps/organizations/domain/ports/organization_invitation_repository.py` + `apps/organizations/infrastructure/persistence/repository/organization_invitation.py` — add `delete_by_id` (or `delete_all_for_email`) to remove invitation rows without stretching `save()` semantics
- `apps/privacy/infrastructure/persistence/schema/__init__.py` — export new ORM
- `shipster/platform/persistence/database.py` — import new ORM in `_register_orm_metadata()`
- `shipster/platform/settings.py` (+ env parsing if present) — `privacy_pending_erasure_poll_seconds`
- `apps/privacy/interfaces/schedule_registration.py` — register erasure poll job
- `apps/privacy/interfaces/dependencies.py` — wire erasure use cases + processor builder
- `shipster/platform/app.py` — `include_router(...)` for erasure router
- `apps/privacy/interfaces/api/__init__.py` — export erasure router symbol if needed

**Optional (defer if you want a thinner v1)**

- `privacy_erasure_lifecycle_events` table + listing endpoint (mirror export timeline)

---

### Task 1: Erasure request persistence (ORM + repo + metadata)

**Files:** create schema/repo; modify `database.py`, `schema/__init__.py`

- [ ] **Add `PrivacyErasureRequestORM`** (`privacy_erasure_requests`)

Suggested columns:

- `id` UUID PK
- `subject_user_id` UUID indexed
- `status` string indexed (`pending`, `processing`, `completed`, `rejected`, `failed`)
- `created_at`, `updated_at` timestamptz
- `failure_reason` nullable text (keep length consistent with export requests)

- [ ] **Implement `SqlAlchemyErasureRequestRepository`** with:

  - `create_pending(subject_user_id) -> PrivacyErasureRequest` (or `save` only—pick one style consistent with export code)
  - `get_by_id`
  - `find_active_for_subject(subject_user_id) -> PrivacyErasureRequest | None` where active ∈ {pending, processing}
  - `list_pending(limit)`
  - `save`

- [ ] **Register ORM** in `shipster/platform/persistence/database.py`

**Verify:** `python3 -m compileall shipster apps`

---

### Task 2: Extend export repository for subject-wide cleanup

**Files:** `export_request_repository.py`, `export_request.py`

- [ ] **Add `list_all_for_subject_user(subject_user_id: UUID) -> list[PrivacyExportRequest]`** ordered by `created_at`

Used by privacy-side erasure step to find export rows + artifact keys.

**Verify:** `compileall`

---

### Task 3: Organizations — invitation deletion support

**Files:** invitation port + SQLAlchemy repo

- [ ] **Add delete API** (choose one):

  - `delete_by_id(invitation_id)` in loop from `list_by_email`, or
  - `delete_all_for_email(email: str)` implemented as `DELETE FROM ... WHERE email == :email`

Normalize email the same way users do (`strip().lower()`).

**Verify:** `compileall`

---

### Task 4: `SubjectDataEraser` ports + infrastructure implementations

**Files:** create ports + erasers; likely touch `apps/users/domain/ports/password_hasher.py` usage only from users eraser (hash a random unusable password)

**Ordering inside processor (locked):**

1. Privacy exports cleanup eraser
2. Organizations invitations eraser (needs **current email** before anonymization)
3. Users anonymize eraser
4. Orders no-op eraser

- [ ] **Privacy eraser (`apps/privacy/infrastructure/erasers/...`)**

  - List export requests for subject
  - For each with `artifact_key`: call `ExportArtifactStorage.delete`
  - Persist export rows to a terminal state consistent with existing semantics (`EXPIRED` is acceptable if you reuse `expire_request`-like behavior without lying about time-based expiry—if that feels wrong, add `FAILED` with a fixed reason string instead)

- [ ] **Organizations eraser**

  - `user = await users.get_by_id(user_id)`; if missing, raise domain error handled by orchestrator
  - `invitations = await invitations.list_by_email(user.email)`
  - delete each row using new delete port

- [ ] **Users eraser**

  - Build anonymized `User` domain object with:

    - **email** unique: e.g. `erased+{user.id.hex}@invalid` (adjust to satisfy uniqueness + length constraints)
    - **username** unique within `String(32)`: must fit DB constraint (derive deterministically from UUID)
    - **password_hash**: set via existing `PasswordHasher.hash(...)` using a random secret generated per anonymization (never stored outside the hash)

- [ ] **Orders eraser**

  - `async def erase_for_user(...): return` (document: no extra PII to erase today)

**Verify:** `compileall`

---

### Task 5: Privacy application orchestration

**Files:** `request_erasure.py`, `get_erasure_status.py`, `process_pending_erasure_requests.py`, `errors.py`, `entities` types

- [ ] **`RequestErasure`**

  - Ensure subject user exists (via `UserRepository.get_by_id` injected from UoW **through interfaces deps**, not imported from domain of users into privacy domain—keep wiring in `apps/privacy/interfaces/dependencies.py`)
  - If active erasure exists → return `409` at router OR return existing id as idempotent `200/202` (pick one and document; recommendation: **`409` conflict**)
  - Create `pending` request

- [ ] **`GetErasureStatus`**

  - AuthZ: subject-only, same “404 not found” style as exports

- [ ] **`ProcessPendingErasureRequests`**

  - Batch `pending` → set `processing` → run erasers in order → `completed`
  - On any unexpected exception: set `failed` with truncated reason string (same style as export failures)

**Verify:** `compileall`

---

### Task 6: HTTP + DI + scheduler + app wiring

**Files:** `privacy_erasure_router.py`, `dependencies.py`, `schedule_registration.py`, `bootstrap.py` (if needed), `settings.py`, `app.py`

- [ ] **Endpoints**

  - `POST /privacy/erasure-requests` → `202` + `{request_id, status}` (`response_model` pydantic model)
  - `GET /privacy/erasure-requests/{request_id}` → status JSON

- [ ] **Dependencies**

  - Mirror export patterns: build erasers using `ShipsterUnitOfWork` repositories + privacy storage

- [ ] **Scheduler**

  - Add `privacy.process_pending_erasure_requests` interval job controlled by `privacy_pending_erasure_poll_seconds`

- [ ] **`create_app()`**

  - `include_router(erasure_router)`

**Verify:** `ruff check/format shipster apps`, `lint-imports`, `compileall`

---

### Task 7: Manual end-to-end verification (required)

- [ ] Create user + membership + invitation-to-email + export request with artifact
- [ ] Request erasure → `pending`
- [ ] Run scheduler tick / wait for poll → `completed`
- [ ] Confirm:

  - invitations to old email are gone
  - user email/username/password no longer usable for login
  - export artifacts removed / export rows terminal

---

## Notes / pitfalls

- **Email vs user_id for invitations:** invitations are keyed by email string; run org eraser **before** anonymizing the user row.
- **Uniqueness:** anonymized `email`/`username` must remain unique per DB constraints.
- **Privacy bounded context imports:** keep `apps/privacy/domain` free of `shipster` and free of other apps’ imports; wire concrete erasers only from `apps/privacy/interfaces/dependencies.py` (same pattern as exporters).
