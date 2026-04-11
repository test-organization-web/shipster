# GDPR Export Request Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an append-only, subject-readable **lifecycle event timeline** for **async** GDPR exports (`privacy_export_requests`), exposed as `GET /privacy/exports/{request_id}/events`.

**Architecture:** Keep all new concepts inside `apps/privacy` (domain entities + ports, application use case(s), SQLAlchemy ORM + repository queries, thin FastAPI router + schemas). Emit lifecycle events **transactionally** whenever export status changes by centralizing writes in `SqlAlchemyExportRequestRepository.save()` (compare previous row vs new domain state).

**Tech stack:** Python 3, FastAPI, SQLAlchemy async, existing Shipster privacy export pipeline (`ProcessPendingExports`, `export_request_lifecycle`).

**Spec:** `docs/superpowers/specs/2026-04-10-gdpr-export-request-timeline-design.md`

**Testing policy note (Shipster workspace):** Do **not** add/expand `tests/` unless the user explicitly asks. Verification is manual + `ruff` + `lint-imports` + `compileall`.

**Repo note:** This workspace may not be a git repository; replace “commit” steps with “checkpoint” (save files) if `git` is unavailable.

---

## File map (what will change)

**Create**

- `apps/privacy/infrastructure/persistence/schema/privacy_export_lifecycle_event.py` — SQLAlchemy model `PrivacyExportLifecycleEventORM` for table `privacy_export_lifecycle_events`
- `apps/privacy/application/list_export_lifecycle_events.py` — `ListExportLifecycleEvents` use case
- (Optional, if you prefer not to overload `ExportRequestRepository`) `apps/privacy/domain/ports/export_lifecycle_event_repository.py` + infra repo — **only** if `save()`-based emission becomes too awkward (YAGNI: try `save()` hook first)

**Modify**

- `apps/privacy/domain/entities.py` — add `PrivacyExportLifecycleEvent`, `PrivacyExportLifecycleEventType` (name as you prefer; keep domain pure)
- `apps/privacy/domain/ports/export_request_repository.py` — add `list_lifecycle_events(...)` + `count_lifecycle_events(...)` (or a single list method that supports offset/limit only)
- `apps/privacy/infrastructure/persistence/repository/export_request.py` — implement listing + **emit lifecycle rows inside `save()`** based on `(old_status -> new_status)` transitions and “insert” path
- `apps/privacy/infrastructure/persistence/schema/__init__.py` — export the new ORM model in `__all__`
- `shipster/platform/persistence/database.py` — import new ORM in `_register_orm_metadata()` so `Base.metadata.create_all` sees the table
- `apps/privacy/interfaces/api/privacy_router.py` — add `GET /{request_id}/events`
- `apps/privacy/interfaces/api/schemas.py` — response models + query params models (limit/offset)
- `apps/privacy/interfaces/dependencies.py` — wire `ListExportLifecycleEvents`

**Do not change (unless you discover a correctness bug)**

- Direct exports now persist `privacy_export_requests` and lifecycle events (same as async); erasure cleanup still targets all rows for the subject.

---

### Task 1: ORM model + metadata registration

**Files:**

- Create: `apps/privacy/infrastructure/persistence/schema/privacy_export_lifecycle_event.py`
- Modify: `apps/privacy/infrastructure/persistence/schema/__init__.py`
- Modify: `shipster/platform/persistence/database.py`

- [ ] **Step 1: Add `PrivacyExportLifecycleEventORM`**

Table: `privacy_export_lifecycle_events`

Columns (minimum):

- `id: Mapped[UUID]` PK
- `export_request_id: Mapped[UUID]` FK → `privacy_export_requests.id`, `nullable=False`, index=True
- `event_type: Mapped[str]` length ~64, index=True
- `occurred_at: Mapped[datetime]` `DateTime(timezone=True)`, index=True

Recommended:

- `actor_user_id: Mapped[UUID | None]` (v1 can set to the export’s `subject_user_id` when known; nullable keeps future flexibility)

FK behavior:

- Prefer `ondelete="CASCADE"` from lifecycle events → export requests (matches retention posture in the spec)

- [ ] **Step 2: Export model from privacy schema package**

Update `apps/privacy/infrastructure/persistence/schema/__init__.py` `__all__`.

- [ ] **Step 3: Register import side-effect**

Update `_register_orm_metadata()` in `shipster/platform/persistence/database.py` to import the new ORM alongside `PrivacyExportRequestORM`.

**Verify:** `python3 -m compileall shipster apps` (expect success)

---

### Task 2: Domain types + repository port extensions

**Files:**

- Modify: `apps/privacy/domain/entities.py`
- Modify: `apps/privacy/domain/ports/export_request_repository.py`

- [ ] **Step 1: Add domain types**

Add:

- `PrivacyExportLifecycleEventType` as `StrEnum` (string values should match the spec doc’s `event_type` strings)
- `PrivacyExportLifecycleEvent` dataclass: `id`, `export_request_id`, `type`, `occurred_at`, optional `actor_user_id`

- [ ] **Step 2: Extend `ExportRequestRepository` protocol**

Add methods (exact signatures up to you, but keep them explicit), e.g.:

- `async def list_lifecycle_events(self, *, export_request_id: UUID, limit: int, offset: int) -> list[PrivacyExportLifecycleEvent]: ...`
- `async def count_lifecycle_events(self, *, export_request_id: UUID) -> int: ...` (optional; can derive via second query)

**Verify:** `python3 -m compileall apps`

---

### Task 3: Implement listing + transactional emission in `SqlAlchemyExportRequestRepository.save`

**Files:**

- Modify: `apps/privacy/infrastructure/persistence/repository/export_request.py`

- [ ] **Step 1: Implement `list_lifecycle_events` / `count_lifecycle_events`**

SQLAlchemy queries against `PrivacyExportLifecycleEventORM`:

- filter `export_request_id == ...`
- order by `occurred_at asc`, `id asc`
- apply `limit`/`offset`

- [ ] **Step 2: Centralize lifecycle emission in `save()`**

On each `save(request)`:

1. `existing = await session.get(PrivacyExportRequestORM, request.id)`
2. Determine `old_status` (if `existing is None`: treat as insert)
3. Perform the existing upsert behavior (add row or mutate fields) — **do not change export semantics**
4. Compute `new_status = request.status`
5. If status changed (or insert), insert 1+ lifecycle rows into `PrivacyExportLifecycleEventORM` using `occurred_at = datetime.now(UTC)` (import UTC consistently with privacy code)

**Transition matrix (minimum required)**

On insert (new export request row):

- Always emit `export_request_created` when the initial saved status is `pending` (current code path)

When `old_status != new_status`:

- `pending -> processing` emit `export_processing_started`
- `processing -> ready` emit `export_ready`
- `processing -> failed` emit `export_failed`
- `ready -> expired` emit `export_expired`
- `ready -> failed` emit `export_failed` (this can happen via `reconcile_ready_request` / missing artifact paths)

**Explicit non-requirements (v1)**

- Do **not** emit download events (per spec).
- Do **not** attempt to track direct exports.

**Edge case guidance**

- If a code path saves the same status twice, emit **nothing** (avoid duplicates).
- If a transition isn’t in the matrix (unexpected), prefer emitting **no event** over guessing; optionally add a debug log in platform only if you already have a standard logging pattern for privacy jobs (keep routers quiet).

**Verify:** `python3 -m compileall apps`

---

### Task 4: Application use case `ListExportLifecycleEvents`

**Files:**

- Create: `apps/privacy/application/list_export_lifecycle_events.py`
- Modify: `apps/privacy/interfaces/dependencies.py` (after use case exists)

- [ ] **Step 1: Implement use case**

Input:

- `request_id: UUID`
- `subject_user_id: UUID`
- `limit: int`, `offset: int` (validated/clamped in interface layer)

Flow:

1. `request = await requests.get_by_id(request_id)`
2. If missing OR `request.subject_user_id != subject_user_id`: raise the same errors used elsewhere (`PrivacyExportNotFoundError` / `PrivacyExportAccessDeniedError` — follow existing `GetDataExportStatus` behavior)
3. List lifecycle events for `request_id` with pagination

Output:

- `total_count` (optional but useful) + `events` list

**Verify:** `python3 -m compileall apps`

---

### Task 5: API: `GET /privacy/exports/{request_id}/events`

**Files:**

- Modify: `apps/privacy/interfaces/api/schemas.py`
- Modify: `apps/privacy/interfaces/api/privacy_router.py`
- Modify: `apps/privacy/interfaces/dependencies.py`

- [ ] **Step 1: Add response schema**

Example fields:

- `id: UUID`
- `type: str` (or enum-like constrained str)
- `occurred_at: datetime`

Optional:

- `actor_user_id: UUID | None`

Add query params model:

- `limit` default 100, le 500
- `offset` default 0, ge 0

- [ ] **Step 2: Router endpoint**

Add route **below** the more specific `/privacy/exports/{request_id}/download` route (or ensure FastAPI routing order won’t capture `events` as an id — safest is to register `/events` paths before `/{request_id}` if needed; adjust ordering if you hit a routing conflict).

Status mapping:

- Mirror `get_export_status` error behavior (`404` for not found/denied)

- [ ] **Step 3: Dependency wiring**

Add `get_list_export_lifecycle_events` similar to existing getters.

**Verify:** start app locally (if you have a standard runner) and hit the endpoint for an async export; if no runner, defer to Task 6 manual checks.

---

### Task 6: Verification + lint gates (required before “done”)

**Files:** n/a (commands)

- [ ] **Step 1: Manual scenario checklist**

- Create an async export → confirm DB contains `export_request_created` event after the initial `save`
- Let worker poll run (`privacy.process_pending_exports`) → confirm `export_processing_started`, then `export_ready`
- Simulate missing artifact / expiry paths already supported by privacy code → confirm `export_failed` / `export_expired` events appear when status transitions happen

- [ ] **Step 2: Run Shipster post-change commands**

Run:

- `lint-imports`
- `ruff check shipster apps`
- `ruff format shipster apps`
- `python3 -m compileall shipster apps`

**Expected:** all succeed.

---

### Task 7: Docs cross-link (small)

**Files:**

- Modify: `docs/superpowers/specs/2026-04-10-gdpr-data-export-design.md` (optional, 1-2 lines)

- [ ] **Step 1: Add a short “Related specs” note** pointing to the timeline spec so readers know export requests may have lifecycle events.

---

## Implementation notes (avoid common pitfalls)

- **Transactional emission:** lifecycle inserts must happen in the same SQLAlchemy session/transaction as export row changes (the scheduler already commits once per poll iteration).
- **SQLite FKs:** if you rely on FK constraints, ensure your DB session/engine enables foreign keys for SQLite in whatever way Shipster already does (if not currently required, still model FK for documentation + Postgres readiness).
- **Performance:** events are tiny; `limit/offset` is fine for v1.

---

## Git checkpoints (if using git)

If git is available, after each task:

```bash
git add apps/privacy shipster/platform/persistence/database.py docs/superpowers/plans/2026-04-10-gdpr-export-request-timeline.md
git commit -m "feat(privacy): export lifecycle timeline"
```

If git is not available, skip commit commands and keep changes grouped logically.
