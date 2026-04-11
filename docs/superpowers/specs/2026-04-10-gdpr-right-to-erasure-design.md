# GDPR Right to Erasure (v1) — Design

## Goal

Let an **authenticated subject** request **erasure of their personal data** held in Shipster, with **durable tracking**, **async processing** for anything non-trivial, and **clear outcomes** (`completed`, `rejected`, `failed`)—without turning `apps/privacy` into a grab-bag of every bounded context’s business rules.

This is **not** full “forget every derived fact everywhere” (search indexes, backups, third-party processors) in v1; it is **in-app data + artifacts** the platform controls.

## Scope (v1)

In scope:

- New **privacy-owned** erasure request aggregate (DB-backed), statuses, and optional **lifecycle event timeline** (same append-only pattern as export timeline).
- **Subject-initiated** flow only (same identity model as exports: current user id).
- **Orchestration in `apps/privacy` application layer**, with **per-bounded-context erasure ports** (mirror `SubjectDataExporter` shape).
- **Async execution** via the existing **scheduler / interval job** pattern (like export processing).
- **Transactional steps per context** where feasible; overall job is **best-effort atomic** (if step 3 fails after 1–2 succeeded, request ends `failed` with reason and ops can intervene—document explicitly).

Explicitly out of scope (v1):

- Admin-initiated erasure, legal hold, DSAR case management UI.
- Erasing or altering **marketplace / carrier** remote systems (treat as follow-up integration work).
- Cryptographic wiping of backups, log redaction across all systems, CDN purge.
- Automatic erasure when **organizations** still depend on the user in ways we have not modeled (see **Blocking**—v1 starts conservative).

## Non-goals / constraints

- **Privacy module must not import other apps’ ORM/repositories directly** from `interfaces`/`application` beyond **small ports** implemented in those apps’ `infrastructure` (same rule as exports).
- **No silent partial success**: the subject should see `failed` or `rejected` with a stable machine-oriented `failure_reason` code/string (human copy can be layered later).
- **Reuse patterns** from data export: hybrid “quick vs async” only if erasure can be proven cheap; default v1 recommendation is **async-only** (simpler, safer).

## Current data model hints (implementation constraints)

- `organization_members.user_id` → `users.id` **ON DELETE CASCADE** (deleting a user removes memberships).
- `orders.user_id` → `users.id` **ON DELETE SET NULL** (orders can remain without a subject link).
- `organization_invitations.invited_by_user_id` → `users.id` **ON DELETE SET NULL**.

These FK behaviors matter when choosing **hard delete user** vs **anonymize-in-place**.

## Erasure strategy (v1 recommendation)

### Recommended default: **anonymize + deactivate** (retain stable internal `user_id`)

Rationale:

- Preserves referential integrity for rows that must remain (orders, audit-like rows) while removing PII from the `users` table.
- Avoids surprising CASCADE deletes of membership rows if we later add constraints that assume “user row exists”.

**Anonymization targets (minimum):**

- `users.email`, `users.username` replaced with non-identifying placeholders **unique per user** (e.g. incorporate random suffix + fixed domain/prefix scheme).
- `users.password_hash` cleared/replaced with an unusable value (force logout everywhere if sessions exist later).

**Follow-up deletes that privacy orchestration should still perform:**

- Remove **privacy export artifacts** and mark export requests **expired/failed** as appropriate (or add a dedicated `superseded_by_erasure` terminal state—pick one; v1 can reuse `expired` + delete artifact keys to avoid schema churn).

### Alternative (explicitly harder): **hard delete `users` row**

Possible if product accepts CASCADE membership deletion and SET NULL order linkage.

If we choose this later, the orchestration order must delete dependent privacy rows first (no FK from privacy tables to users today, but artifacts and requests still reference `subject_user_id` as data).

**v1 decision:** implement **anonymize + deactivate** unless product explicitly chooses hard delete during spec review.

## Architecture

### Privacy domain

Add:

- `PrivacyErasureRequest` entity + `PrivacyErasureStatus` enum (`pending`, `processing`, `completed`, `rejected`, `failed`)
- Domain errors: not found, access denied, subject not found, **erasure not allowed** (rejected), conflict (duplicate open request)

Optional (recommended for parity with exports):

- `privacy_erasure_lifecycle_events` append-only table + `PrivacyErasureLifecycleEventType`

### Privacy application

Use cases (names indicative):

- `request_erasure` — validates subject, creates durable `pending` request, schedules processing
- `get_erasure_status`
- `list_erasure_lifecycle_events` (optional v1.1 if we want to ship statuses first)

Processor:

- `process_pending_erasure_requests` — batch like exports

### Per-context ports (new)

Mirror exporters:

```text
apps/privacy/domain/ports/subject_data_eraser.py
  SubjectDataEraser Protocol:
    async def erase_for_user(self, user_id: UUID) -> None: ...
```

Implementations live in:

- `apps/users/infrastructure/erasers/...`
- `apps/organizations/infrastructure/erasers/...`
- `apps/orders/infrastructure/erasers/...` (may be no-op in v1 if no PII columns beyond `user_id` already nullable)

**Ordering (v1):**

1. `privacy` internal cleanup (exports/artifacts tied to subject)
2. `organizations` (invitations that embed email PII; memberships fall out of anonymize/delete strategy)
3. `users` (anonymize user record)
4. `orders` (optional scrub if future PII appears)

## Blocking / rejection rules (v1)

Start conservative to avoid accidental org breakage:

- **Reject** if there is at least one **organization membership** for the subject **where the member is the only member** OR where the subject is the **last admin**—*only if* the organizations module already exposes enough data to decide this reliably. If not available without new queries/ports, v1 can **defer** this rule and instead document “known limitation”.

Minimum viable rules (always implement):

- Reject if user does not exist.
- Reject if there is already an erasure request in `pending` or `processing` for that subject (idempotency policy: return existing request id vs `409`—pick one and document).

## API (v1)

Prefix suggestion: `/privacy/erasure` (singular resource) or `/privacy/erasure-requests` (collection). Pick one style and keep exports under `/privacy/exports`.

Endpoints:

- `POST /privacy/erasure-requests` → `202` with `{request_id, status}` (async-only v1)
- `GET /privacy/erasure-requests/{request_id}` → status + timestamps + `failure_reason` / `rejection_reason`

Optional:

- `GET /privacy/erasure-requests/{request_id}/events` (lifecycle timeline)

**HTTP mapping:** keep routers thin; map domain errors like exports (`404` for denied/not found).

## Persistence

- Table `privacy_erasure_requests` (similar columns to export requests: id, subject_user_id, status, timestamps, failure/rejection reason).
- Optional `privacy_erasure_lifecycle_events` with FK `ON DELETE CASCADE`.

ORM registration must be added to `shipster/platform/persistence/database.py` import registry (same mechanism as exports).

## Scheduler

Add `privacy.process_pending_erasure_requests` interval job alongside export polling, controlled by settings key(s) mirroring export poll seconds.

## Verification (v1)

Manual:

- Create erasure request → pending
- Worker processes → completed
- Verify user row PII fields are anonymized and user cannot log in
- Verify export artifacts removed / export rows terminal

## Open questions (answer during review)

1. **Hard delete vs anonymize** for `users` (see above).
2. **Org safety rule**: enforce “not sole member / not last admin” in v1, or ship without it and document risk?
3. **Email invitations**: should erasure delete pending invitations **to** the subject email, invitations **by** the subject, or both?

---

## Approval

After this spec is approved, the implementation plan should live at:

- `docs/superpowers/plans/2026-04-10-gdpr-right-to-erasure.md`
