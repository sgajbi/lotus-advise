# RFC-0023: DPM Persistent Supportability Store and Lineage APIs

| Metadata | Details |
| --- | --- |
| **Status** | IN_PROGRESS |
| **Created** | 2026-02-20 |
| **Depends On** | RFC-0017, RFC-0018, RFC-0019 |
| **Doc Location** | `docs/rfcs/RFC-0023-dpm-persistent-supportability-store-and-lineage-apis.md` |

## 1. Executive Summary

Add durable persistence and lineage APIs for DPM supportability data so operations teams can investigate historical runs, operation chains, and idempotency behavior beyond process lifetime.

## 2. Problem Statement

In-memory supportability works for local/runtime diagnostics but is insufficient for enterprise incident response, auditability, and long-horizon lineage tracing.

## 3. Goals and Non-Goals

### 3.1 Goals

- Introduce persistence adapter contract for run, operation, artifact, and idempotency lookup data.
- Add filtered query APIs for lineage and support investigations.
- Keep API contracts stable across in-memory and durable adapters.

### 3.2 Non-Goals

- Mandate a single database vendor.
- Build cross-system observability dashboards in this RFC.

## 4. Proposed Design

### 4.1 Storage Adapter Contract

- Abstract repository interfaces for:
  - run metadata
  - operation metadata
  - artifact payload references
  - idempotency records
  - lineage edges (`caused_by`, `replayed_from`, `derived_from`)

### 4.2 API Surface

- `GET /rebalance/runs?from=...&to=...&status=...&portfolio_id=...`
- `GET /rebalance/supportability/summary`
- `GET /rebalance/lineage/{entity_id}`
- `GET /rebalance/idempotency/{idempotency_key}/history`

### 4.3 Configurability

- `DPM_SUPPORTABILITY_STORE_BACKEND` (`IN_MEMORY` | `SQL`)
- `DPM_SUPPORTABILITY_RETENTION_DAYS`
- `DPM_SUPPORTABILITY_SUMMARY_APIS_ENABLED` (default `true`)
- `DPM_LINEAGE_APIS_ENABLED` (default `false`)
- `DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED` (default `false`)

## 5. Test Plan

- Repository contract tests runnable against in-memory and SQL adapters.
- API filtering tests.
- Data retention policy tests.
- Lineage traversal correctness tests.

## 6. Rollout/Compatibility

Ship SQL adapter behind configuration, keep in-memory as default for local development. APIs are additive and backward compatible.

## 7. Status and Reason Code Conventions

No new business run statuses. Investigation responses use explicit technical status codes and stable reason code fields when applicable.

## 8. Implementation Status

- Implemented (slice 1):
  - Repository backend selection:
    - `DPM_SUPPORTABILITY_STORE_BACKEND` (`IN_MEMORY` | `SQLITE`)
    - `DPM_SUPPORTABILITY_SQLITE_PATH` (SQLite database file path)
  - SQLite repository adapter for DPM supportability records:
    - runs
    - idempotency mappings
    - async operations
    - workflow decisions
  - Contract tests validating repository parity between in-memory and SQLite adapters.
- Implemented (slice 2):
  - Lineage API:
    - `GET /rebalance/lineage/{entity_id}`
  - Lineage edge recording for:
    - correlation to run
    - idempotency key to run
    - async operation id to correlation id
  - Feature flag:
    - `DPM_LINEAGE_APIS_ENABLED` (default `false`)
- Implemented (slice 3):
  - Idempotency history API:
    - `GET /rebalance/idempotency/{idempotency_key}/history`
  - Persistent append-only idempotency history storage for both backends:
    - in-memory
    - SQLite
  - Feature flag:
    - `DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED` (default `false`)
- Implemented (slice 4):
  - Run listing API:
    - `GET /rebalance/runs`
      - filters: `from`, `to`, `status`, `portfolio_id`
      - pagination: `limit`, `cursor`
- Implemented (slice 5):
  - Retention policy:
    - `DPM_SUPPORTABILITY_RETENTION_DAYS`
  - Automatic purge of expired supportability run records and derived mappings/edges.
- Implemented (slice 6):
  - Async operation listing API:
    - `GET /rebalance/operations`
      - filters: `from`, `to`, `operation_type`, `status`, `correlation_id`
      - pagination: `limit`, `cursor`
- Implemented (slice 7):
  - Supportability summary API:
    - `GET /rebalance/supportability/summary`
      - returns run count, async operation count, operation status distribution, and created-at bounds.
  - Feature flag:
    - `DPM_SUPPORTABILITY_SUMMARY_APIS_ENABLED` (default `true`)
- Pending:
  - SQL backend beyond SQLite (enterprise managed database deployment profile).
