# RFC-0023: DPM Persistent Supportability Store and Lineage APIs

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
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
- `GET /rebalance/lineage/{entity_id}`
- `GET /rebalance/idempotency/{idempotency_key}/history`

### 4.3 Configurability

- `DPM_SUPPORTABILITY_STORE_BACKEND` (`IN_MEMORY` | `SQL`)
- `DPM_SUPPORTABILITY_RETENTION_DAYS`
- `DPM_LINEAGE_APIS_ENABLED` (default `false`)

## 5. Test Plan

- Repository contract tests runnable against in-memory and SQL adapters.
- API filtering tests.
- Data retention policy tests.
- Lineage traversal correctness tests.

## 6. Rollout/Compatibility

Ship SQL adapter behind configuration, keep in-memory as default for local development. APIs are additive and backward compatible.

## 7. Status and Reason Code Conventions

No new business run statuses. Investigation responses use explicit technical status codes and stable reason code fields when applicable.

