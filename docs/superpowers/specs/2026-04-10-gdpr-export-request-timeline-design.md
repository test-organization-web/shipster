# GDPR Export Request Timeline (Privacy Tracking) — Design

## Goal

Give subjects an **append-only lifecycle timeline** for **async** GDPR data export requests, so they can see how an export progressed over time (created → processing → terminal state), without turning privacy tracking into a generalized “all rights” system yet.

## Scope (v1)

In scope:

- Persist **lifecycle-only** events for exports backed by `privacy_export_requests` (async path).
- Expose a **subject-authenticated read API** to fetch the timeline for a single export request they own.
- Keep events **non-sensitive**: no exporter payloads, no artifact bytes, no request/response bodies.

Explicitly out of scope (v1):

- Download/access attempt auditing (user chose lifecycle-only).
- Tracking **direct synchronous exports** (user chose async-only timeline).
- General privacy ledger spanning multiple rights (e.g., erasure) — future work.
- Admin/support consoles, cross-tenant reporting, SIEM pipelines.

## Non-goals / constraints

- **Direct exports are tracked too**: synchronous exports still create `privacy_export_requests` rows (through `ready` with an artifact) so lifecycle events and `/privacy/exports/{id}` apply; the response file also includes `X-Privacy-Export-Request-Id` for discovery.
- **No PII in event metadata**: if metadata is needed later, it must be strictly categorized and reviewed (default v1: no free-form metadata; rely on typed `event_type` + timestamps).

## Current baseline (context)

Async exports already persist durable rows in `privacy_export_requests` and expose status via `/privacy/exports/{request_id}`.

This timeline feature is an **additive** observability layer on top of that row: it should not replace the existing status field, but should explain transitions over time.

## Architecture

Stay within `apps/privacy`:

- **Domain**: define `PrivacyExportLifecycleEvent` + `PrivacyExportLifecycleEventType` (or similar) as pure types; define a small port to append/list events.
- **Application**: emit events whenever export lifecycle state changes (single-writer principle: state transitions should append events in the same transaction as persisting the new status).
- **Infrastructure**: add a new SQLAlchemy table + repository implementation.
- **Interfaces**: add a thin FastAPI endpoint under the existing `/privacy/exports` prefix.

### Event model

Append-only table (name suggestion): `privacy_export_lifecycle_events`

Suggested columns:

- `id` (UUID, PK)
- `export_request_id` (UUID, FK → `privacy_export_requests.id`, indexed)
- `event_type` (string/enum, indexed)
- `occurred_at` (timestamptz, indexed)
- optional: `actor_user_id` (UUID, nullable) — v1 can always set to the subject user id for subject-initiated exports, but keeping nullable leaves room for future internal actors without redesigning the row

Suggested `event_type` values (v1):

- `export_request_created` — row inserted in `pending` (or initial state)
- `export_processing_started` — moved to `processing`
- `export_ready` — moved to `ready`
- `export_failed` — moved to `failed` (failure details remain on the export request row; not duplicated into events)
- `export_expired` — moved to `expired`

Rules:

- `occurred_at` should reflect the transition time as closely as practical (typically `datetime.now(UTC)` in the same transaction as the status update).
- The API must return a **stable ordering** (`occurred_at`, then `id`) even if clocks skew or multiple transitions happen in one transaction.
- **Transactional rule**: lifecycle events must commit in the **same database transaction** as the export request status update that they describe (no “status updated but event missing” states after commit).

### API

Add:

- `GET /privacy/exports/{request_id}/events`

Behavior:

- AuthN: same subject user as existing export endpoints.
- AuthZ: same “not found” behavior as status/download for cross-subject access (`404`).

Response shape (conceptual):

- ordered list of `{id, type, occurred_at}`

Pagination (v1 recommendation):

- Use `limit` + `offset` with sane caps (`limit` default 100, max 500). This is expected to be low-volume; we can evolve to cursor pagination later if needed.

### Repository / UoW interaction

Prefer implementing event persistence via the same session as export request updates:

- Option A (preferred): extend the existing `ExportRequestRepository` implementation to also write events in `save()` / dedicated methods used by lifecycle code.
- Option B: separate `ExportLifecycleEventRepository` port, but wire it with the same SQLAlchemy `Session` per request/job to preserve atomicity.

## Failure modes

- **Duplicate transitions**: application layer should avoid writing duplicate terminal events; if a bug double-writes, API should still be correct (append-only), ops can detect anomalies.
- **Backfill**: existing historical rows may have no events; v1 can return an empty list or optionally add a one-time migration/backfill script — decision: **no automatic backfill** in v1 unless explicitly requested (keep scope tight).

## Retention

Lifecycle events inherit the same retention posture as export requests:

- If export requests are deleted/purged, events should be deleted via FK `ON DELETE CASCADE` (recommended) or explicit purge job later.

## Security & privacy notes

- Do not log exporter payloads when recording lifecycle transitions.
- Keep router thin; mapping stays in interfaces; orchestration stays in application.

## Verification (v1)

Manual checks:

- Create async export → observe `created` + later `processing`/`ready` events via new endpoint.
- Force a failure path → `failed` event appears alongside `failure_reason` on export row.
- Expiry path → `expired` event appears when status becomes expired.

Automated tests only if the user explicitly requests them (workspace policy).

## Persistence / migrations

Adding `privacy_export_lifecycle_events` requires a DB migration consistent with the project’s existing migration approach (Alembic if enabled; otherwise follow the repo’s established schema update process).

## Implementation follow-up

After this spec is reviewed/approved, write an implementation plan at:

- `docs/superpowers/plans/2026-04-10-gdpr-export-request-timeline.md`
