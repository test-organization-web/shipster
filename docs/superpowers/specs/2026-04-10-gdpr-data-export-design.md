# GDPR Data Export Design

## Goal

Add a user-facing GDPR data export capability that lets an authenticated subject request a copy of their data from the system. The first version should support a hybrid delivery model: return a file immediately for small exports, and create a tracked export job plus later download for larger exports.

**Related:** append-only **async export lifecycle timeline** (subject-readable API) is specified in `docs/superpowers/specs/2026-04-10-gdpr-export-request-timeline-design.md`.

## Scope

This spec covers only `data export`.

It does not include:

- erasure or anonymization workflows
- generalized privacy request handling beyond export requests
- cross-system vendor exports
- object storage or external artifact hosting

## Architecture

Introduce a new bounded context: `apps/privacy`.

Responsibilities:

- own export request entities and statuses
- orchestrate export assembly across bounded contexts
- decide direct vs async delivery
- store export request metadata
- delegate artifact persistence to a storage port

Keep existing bounded contexts responsible for their own data shape. Each context should expose a focused export port consumed by the privacy application layer.

Initial exporter coverage:

- `users`
- `organizations`
- `orders`

The privacy module should not know repository internals for those contexts. It should depend only on small export-facing ports.

## Components

### Privacy Domain

Create domain types for:

- `PrivacyExportRequest`
- `PrivacyExportStatus`
- `PrivacyExportArtifact`

Suggested statuses:

- `pending`
- `processing`
- `ready`
- `failed`
- `expired`

Create domain ports for:

- export request repository
- export artifact storage
- per-context subject exporters

### Privacy Application

Create use cases for:

- `create_data_export`
- `get_data_export_status`
- `download_data_export`

`create_data_export` should:

1. authenticate the subject through the router/dependency layer
2. estimate whether the export is small enough for direct generation
3. either return an immediate file result or persist an export request and schedule/trigger async processing

If the system cannot determine export size cheaply or confidently, it should choose the async path by default.

### Privacy Interfaces

Add a new router under a dedicated prefix such as `/privacy/exports`.

Initial endpoints:

- `POST /privacy/exports`
- `GET /privacy/exports/{request_id}`
- `GET /privacy/exports/{request_id}/download`

Routers remain thin:

- parse input
- resolve authenticated user
- call privacy use case
- map errors to HTTP

### Privacy Infrastructure

Implement:

- DB-backed export request repository
- local-file artifact storage adapter
- exporter adapters for `users`, `organizations`, and `orders`

The first storage implementation may keep:

- metadata in DB
- artifact file on local disk

Artifact storage must stay behind a port so it can later move to object storage without changing privacy use cases.

## Delivery Model

Use a hybrid approach.

### Direct path

For small exports:

- gather all exporter data in request flow
- build one JSON document
- persist a `privacy_export_requests` row through `pending` → `processing` → `ready` and store the same bytes as a durable artifact (so status, download, and lifecycle events work like async)
- return a `FileResponse` for immediate download (response includes `X-Privacy-Export-Request-Id` so clients can correlate without parsing the file)

FastAPI guidance supports direct file downloads with `FileResponse`, which fits this path well.

### Async path

For larger exports:

- create an export request row with `pending`
- process the request out of band
- store the artifact
- mark status `ready`
- let the user poll and later download

For the first implementation, the exact async trigger may be a dedicated scheduler/worker integration or another explicit out-of-band processor, but it must run with fresh resources outside the original request lifecycle.

Do not model this as a request-bound background task using request-scoped resources. Current FastAPI guidance recommends background work create its own resources instead of reusing dependency-managed request resources.

## Export Document Shape

Produce one canonical JSON export document with top-level sections by bounded context.

Suggested shape:

```json
{
  "meta": {
    "subject_user_id": "uuid",
    "generated_at": "iso-datetime",
    "schema_version": 1
  },
  "users": {},
  "organizations": {},
  "orders": {}
}
```

Rules:

- each bounded context owns its own subdocument shape
- privacy orchestrator only assembles the final envelope
- do not silently omit failed sections

If any exporter fails, fail the whole export request.

## Data Flow

### Direct export flow

1. client calls `POST /privacy/exports`
2. router authenticates the current user
3. privacy use case evaluates export size/cost
4. privacy use case calls exporter ports for `users`, `organizations`, and `orders`
5. privacy use case assembles export JSON, persists request + artifact, then returns a download file immediately

### Async export flow

1. client calls `POST /privacy/exports`
2. router authenticates the current user
3. privacy use case decides export is too large for direct response
4. privacy use case creates export request metadata with `pending`
5. worker/job processes the request using fresh resources
6. artifact is stored and request becomes `ready` or `failed`
7. client polls `GET /privacy/exports/{request_id}`
8. client downloads from `GET /privacy/exports/{request_id}/download`

## Access Control

Only the authenticated subject who created an export request may view its status or download its artifact.

Rules:

- request ownership must be checked in privacy application logic
- download endpoints must not expose filesystem paths
- router error responses should be generic (`not found`, `not ready`, `failed`)

## Error Handling

If exporter aggregation fails:

- direct path returns an application error mapped to HTTP failure
- async path stores `failed` status and an internal diagnostic message

Do not return internal exporter details to clients.

Expected client-visible states:

- request accepted
- ready for download
- not ready yet
- failed
- not found
- expired

## Retention

Export artifacts should expire after a short retention window.

Initial rule:

- metadata remains for audit/debug visibility
- artifact file is deleted after expiry
- expired requests return `expired` and no longer download

Retention duration should be configurable in a later phase if needed. It does not need to block the first implementation.

## Logging And Privacy

Do not log export contents or generated files.

Allowed logging:

- request id
- subject user id
- status transitions
- duration/size metadata where useful

Avoid:

- raw export payload logging
- artifact path exposure in user-facing responses

## Testing Strategy

Per current project rule, do not add or modify tests unless explicitly requested by the user.

Implementation should still be structured for future focused tests:

- exporter ports are small and swappable
- privacy orchestration is isolated in application use cases
- storage remains behind a port

For implementation completion, verify with:

- `ruff format shipster apps`
- `ruff check shipster apps`
- `python3 -m compileall shipster apps`
- `.venv/bin/lint-imports`

## Recommended File Structure

Suggested initial layout:

```text
apps/privacy/
  domain/
    entities.py
    errors.py
    ports/
      export_request_repository.py
      export_artifact_storage.py
      subject_data_exporter.py
  application/
    create_data_export.py
    get_data_export_status.py
    download_data_export.py
  infrastructure/
    persistence/
    storage/
    exporters/
  interfaces/
    api/
```

## Recommendation

Implement this as a standalone `apps/privacy` bounded context with a hybrid delivery model.

That gives:

- a clean architectural boundary
- a fast happy path for small accounts
- a scalable path for larger exports
- a natural foundation for later erasure and privacy request tracking
