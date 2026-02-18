# RFC-0015: Deferred Scope Consolidation and Completion Backlog

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
| **Created** | 2026-02-18 |
| **Depends On** | RFC-0001 to RFC-0013 |
| **Doc Location** | docs/rfcs/RFC-0015-deferred-scope-consolidation-and-completion-backlog.md |

---

## 0. Executive Summary

RFC-0001 to RFC-0013 are implemented. This RFC consolidates all explicitly deferred or pending items into one completion backlog so future work is tracked in a single place.

Goals:
1. Normalize cross-RFC deferred scope into one list.
2. Define implementation slices for outstanding items.
3. Preserve current behavior unless explicitly expanded.

---

## 1. Problem Statement

Deferred items are currently spread across multiple RFCs and sections. This creates ambiguity about what remains outstanding versus what is already implemented behind request options.

---

## 2. Goals and Non-Goals

### 2.1 Goals
1. Track all outstanding deferred scope from RFC-0001 to RFC-0013.
2. Define clear milestones and acceptance criteria for each item.
3. Keep existing API routes and status semantics unchanged.

### 2.2 Non-Goals
1. Implementing execution connectivity (OMS/FIX).
2. Replacing existing deterministic single-run semantics.
3. Backfilling historical persistence data.

---

## 3. Consolidated Deferred Backlog

### 3.1 Persistence and Idempotency (from RFC-0001, RFC-0002, RFC-0006A, RFC-0007A)
1. Persistence-backed rebalance run storage.
2. Durable idempotency key/hash replay logic.
3. Conflict detection semantics for duplicate idempotency keys.

### 3.2 Error and Operational Contract Hardening (from RFC-0001, RFC-0002)
1. Optional RFC-7807-compatible domain error envelope strategy (without breaking current status-in-body contract).
2. End-to-end observability expansion:
   1. stage latency metrics
   2. data-quality counters
   3. correlation propagation consistency

### 3.3 Turnover and Cost Expansion (from RFC-0010)
1. Explicit transaction-cost model terms:
   1. spread
   2. commissions
   3. slippage/impact assumptions
2. Partial intent sizing under turnover/cost limits.

### 3.4 Batch Analytics Expansion (from RFC-0013)
1. Batch-level tax-impact comparison metrics (scenario-to-scenario).
2. Optional aggregate ranking fields for scenario selection.

### 3.5 Tax and Settlement Advanced Scope (from RFC-0009, RFC-0011)
1. Configurable lot policy (`HIFO`, `FIFO`, `LIFO`) with deterministic tie-breaking.
2. Optional per-instrument tax budget overlays.
3. Pair-specific FX settlement calendars.

### 3.6 Solver Expansion (from RFC-0012)
1. Solver governance policy:
   1. when to auto-select solver
   2. fallback policy and diagnostics
2. Explicit compatibility policy between solver mode and advanced tax/settlement constraints.

---

## 4. Delivery Plan

1. RFC-0015A: Persistence and idempotency storage.
2. RFC-0015B: Cost model and partial sizing.
3. RFC-0015C: Batch tax analytics.
4. RFC-0015D: Tax/settlement advanced policy controls.
5. RFC-0015E: Solver governance and compatibility matrix.

---

## 5. Test Plan

For each RFC-0015 slice:
1. Contract tests for new fields and validations.
2. Engine behavior tests for deterministic branch logic.
3. API tests for request/response compatibility.
4. Golden scenarios for business-critical outcomes.

---

## 6. Compatibility and Safety

1. Canonical endpoints remain:
   1. `POST /rebalance/simulate`
   2. `POST /rebalance/analyze`
2. Top-level statuses remain:
   1. `READY`
   2. `PENDING_REVIEW`
   3. `BLOCKED`
3. Existing safety invariants remain mandatory:
   1. no-shorting safeguards
   2. insufficient cash safeguard
   3. reconciliation mismatch block

---

## 7. Status and Reason Code Conventions

1. New reason/warning codes introduced by RFC-0015 slices must use upper snake case.
2. RFC-0015 does not introduce new top-level run statuses.
