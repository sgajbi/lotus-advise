# RFC-0024: Unified PostgreSQL Persistence for DPM and Advisory

| Metadata | Details |
| --- | --- |
| **Status** | IN PROGRESS (SLICE 8) |
| **Created** | 2026-02-20 |
| **Depends On** | RFC-0014G, RFC-0017, RFC-0018, RFC-0019, RFC-0020, RFC-0023 |
| **Doc Location** | `docs/rfcs/RFC-0024-unified-postgresql-persistence-for-dpm-and-advisory.md` |

## 1. Executive Summary

Adopt PostgreSQL as the shared durable persistence backend for both DPM and advisory supportability/workflow lifecycles, using a common schema vocabulary and repository contracts while preserving existing API behavior.

## 2. Problem Statement

Current state is split between in-memory adapters (advisory and default DPM) and SQLite (optional DPM backend). This is useful for incremental delivery but not sufficient for enterprise scale, concurrency, audit retention, and operational consistency across both businesses.

## 3. Goals and Non-Goals

### 3.1 Goals

- Standardize on PostgreSQL for durable production persistence in both engines.
- Reuse common naming and storage patterns across DPM and advisory where domain concepts overlap.
- Preserve backward-compatible API contracts and feature-flagged rollout controls.
- Introduce migration discipline for schema evolution.

### 3.2 Non-Goals

- Build BI/reporting warehouse models in this RFC.
- Replace all local-development in-memory flows.
- Introduce breaking API contract changes.

## 4. Proposed Design

### 4.1 Backend Targets

- DPM supportability repository:
  - runs
  - idempotency mappings
  - async operations
  - workflow decisions
  - lineage edges (from RFC-0023 continuation)
- Advisory proposal lifecycle repository:
  - proposal aggregates
  - immutable versions
  - workflow events
  - approvals
  - idempotency mappings
  - async operations

### 4.2 Unified Vocabulary and Modeling Rules

- Shared technical concepts:
  - `correlation_id`
  - `idempotency_key`
  - `request_hash`
  - `created_at`, `updated_at`
  - append-only event/decision records
- Domain-specific states stay separated:
  - DPM run workflow states and actions
  - advisory proposal workflow states and events
- Persist canonical JSON snapshots for deterministic replay and artifact rebuilding.

### 4.3 Migration and Tooling

- Introduce schema migration tooling and versioned migration files.
- Enforce forward-only migrations for production paths.
- Add repository contract tests runnable against:
  - in-memory adapters
  - SQLite adapters (optional local profile)
  - PostgreSQL adapters (CI integration profile)

### 4.4 Configurability

- DPM:
  - extend `DPM_SUPPORTABILITY_STORE_BACKEND` to include `POSTGRES`
  - connection config via `DPM_SUPPORTABILITY_POSTGRES_DSN`
- Advisory:
  - add `PROPOSAL_STORE_BACKEND` (`IN_MEMORY` | `POSTGRES`)
  - connection config via `PROPOSAL_POSTGRES_DSN`

### 4.5 Rollout Phases

1. Schema baseline and Postgres adapters behind flags.
2. Dual-run verification (in-memory/SQLite vs Postgres parity checks).
3. Enable Postgres in non-prod, then prod.
4. Keep in-memory fallback for local/dev tests.

## 5. Test Plan

- Contract tests for repository parity across backends.
- API regression suite with Postgres backend enabled for DPM and advisory.
- Migration smoke tests on empty and pre-seeded databases.
- Determinism tests for artifact and replay-related payloads after persistence.

## 6. Rollout/Compatibility

- Feature-flagged and additive.
- Existing APIs remain unchanged.
- Existing default local behavior remains available.
- Postgres becomes recommended production backend for both domains.

## 7. Status and Reason Code Conventions

- No change to business status vocabularies:
  - DPM run status: `READY`, `PENDING_REVIEW`, `BLOCKED`
  - DPM workflow status: `NOT_REQUIRED`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`
  - advisory workflow states remain as defined in RFC-0014G
- Reason code naming remains uppercase snake case.

## 8. Implementation Status

- Implemented (slice 1):
  - DPM supportability backend contract now recognizes `POSTGRES` in configuration.
  - Added DSN setting:
    - `DPM_SUPPORTABILITY_POSTGRES_DSN`
  - Guardrail behavior for early rollout:
    - missing DSN raises `DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED`
    - placeholder backend mode currently raises `DPM_SUPPORTABILITY_POSTGRES_NOT_IMPLEMENTED`
  - Existing default behavior remains unchanged (`IN_MEMORY` by default, `SQL`/`SQLITE` path unchanged).
- Implemented (slice 2):
  - Added `PostgresDpmRunRepository` backend scaffold and factory wiring for DPM supportability.
  - Initialization guardrails:
    - missing DSN raises `DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED`
    - missing `psycopg` dependency raises `DPM_SUPPORTABILITY_POSTGRES_DRIVER_MISSING`
  - Unimplemented operations currently fail explicitly with:
    - `DPM_SUPPORTABILITY_POSTGRES_NOT_IMPLEMENTED`
  - API guardrail:
    - supportability endpoints map backend initialization errors to HTTP `503` with explicit
      detail codes (for example DSN/driver issues).
- Implemented (slice 3):
  - Added pinned runtime dependency:
    - `psycopg[binary]==3.3.3`
  - Added Docker Compose Postgres runtime profile:
    - `docker-compose --profile postgres up -d --build`
    - `postgres:17.6` with healthcheck and persistent named volume.
  - Added deployment documentation for:
    - `DPM_SUPPORTABILITY_STORE_BACKEND=POSTGRES`
    - `DPM_SUPPORTABILITY_POSTGRES_DSN=...`
- Implemented (slice 4):
  - Added concrete Postgres supportability repository subset:
    - `save_run`
    - `get_run`
    - `save_run_artifact`
    - `get_run_artifact`
  - Added table bootstrap for:
    - `dpm_runs`
    - `dpm_run_artifacts`
  - Added repository unit coverage using fake Postgres connection semantics to validate
    deterministic SQL adapter behavior without external DB dependency.
- Implemented (slice 5):
  - Added concrete Postgres supportability repository operations for:
    - idempotency mapping CRUD
    - idempotency history append/list
    - async operation create/update/get/list
    - async operation TTL purge
  - Added table bootstrap for:
    - `dpm_run_idempotency`
    - `dpm_run_idempotency_history`
    - `dpm_async_operations`
  - Added deterministic unit coverage for filters, cursor behavior, and purge semantics.
- Implemented (slice 6):
  - Added concrete Postgres supportability repository operations for:
    - workflow decisions append/list/list-filtered
    - lineage edges append/list
    - supportability summary aggregation
    - run retention purge with related-entity cleanup
  - Added table bootstrap for:
    - `dpm_workflow_decisions`
    - `dpm_lineage_edges`
  - Added unit coverage for:
    - workflow filtering and cursor behavior
    - lineage retrieval by source/target entity
    - summary counters and status distributions
    - retention purge cascade behavior
- Implemented (slice 7):
  - Added concrete Postgres run lookup/list parity helpers:
    - `get_run_by_correlation`
    - `get_run_by_request_hash`
    - `list_runs`
  - Added unit coverage for:
    - run listing filters (`from`, `to`, `status`, `request_hash`, `portfolio_id`)
    - run listing cursor paging and invalid cursor behavior
    - correlation/request-hash lookup semantics
- Implemented (slice 8):
  - Added live Postgres repository integration contract tests (docker-gated) covering:
    - run persistence, lookups, filters, cursor pagination, and artifact retrieval
    - idempotency mapping/history, workflow decisions, lineage edges, and summary aggregation
    - async operation pagination/TTL purge and run retention cascade purge semantics
  - Test runtime guard:
    - tests run only when `DPM_POSTGRES_INTEGRATION_DSN` is set.
  - Manual runtime validation completed on `2026-02-20`:
    - uvicorn with `POSTGRES` backend
    - Docker container runtime with `POSTGRES` backend
    - simulate -> run lookup by correlation -> supportability summary flow validated.
- Next slice:
  - advisory Postgres repository parity implementation and contract tests.
