# RFC-0015: Deferred Scope Consolidation and Completion Backlog

| Metadata | Details |
| --- | --- |
| **Status** | SUPERSEDED (TRIAGED) |
| **Created** | 2026-02-18 |
| **Depends On** | RFC-0001 to RFC-0013 |
| **Doc Location** | docs/rfcs/RFC-0015-deferred-scope-consolidation-and-completion-backlog.md |

---

## 0. Executive Summary

RFC-0015 originally consolidated deferred items after RFC-0001 to RFC-0013. Since then, most high-value backlog items were implemented through dedicated RFCs (RFC-0016 to RFC-0023), and some legacy candidates no longer add sufficient business value.

This document is now a triage/closure artifact:
1. Mark covered items as completed by later RFCs.
2. Discard low-value or high-risk/low-return items.
3. Keep only meaningful remaining candidates for future standalone RFCs.

---

## 1. Problem Statement

RFC-0015 as a single umbrella backlog is no longer the best planning tool. The platform now uses focused, testable RFC slices. Keeping a broad umbrella backlog creates noise and duplicate tracking.

---

## 2. Goals and Non-Goals

### 2.1 Goals
1. Keep only actionable, business-relevant items.
2. Remove stale items already implemented elsewhere.
3. Avoid carrying low-value scope that dilutes roadmap focus.

### 2.2 Non-Goals
1. Implementing remaining scope directly under RFC-0015.
2. Reintroducing umbrella slicing (`RFC-0015A/B/C/...`) as a delivery model.

---

## 3. Triage Outcome

### 3.1 Covered by Later RFCs (Closed)
1. Persistence-backed run/idempotency/supportability storage:
   - Covered by RFC-0016, RFC-0017, RFC-0018, RFC-0019, RFC-0020, RFC-0023.
2. Durable supportability and lineage APIs:
   - Covered by RFC-0017, RFC-0018, RFC-0023.
3. OpenAPI contract hardening and request/response separation:
   - Covered by RFC-0021.
4. Configurable policy-pack controls:
   - Covered by RFC-0022.

### 3.2 Discarded (Low Value or Wrong Timing)
1. Optional RFC-7807 domain envelope migration in current phase:
   - Discarded for now due integration churn risk versus limited near-term value.
2. Umbrella mixed-scope delivery plan (`RFC-0015A` to `RFC-0015E`):
   - Discarded in favor of focused standalone RFCs.
3. Generic batch scenario ranking fields without clear business workflow:
   - Discarded unless a concrete consumer/use-case is defined.

### 3.3 Remaining High-Value Candidates (Keep)
1. Transaction-cost model expansion:
   - spread, commissions, slippage/impact assumptions
   - partial intent sizing under turnover/cost limits
2. Advanced tax/settlement policy controls:
   - deterministic configurable lot policy (`HIFO`/`FIFO`/`LIFO`)
   - optional per-instrument tax budget overlays
   - pair-specific FX settlement calendars
3. Solver governance and compatibility policy:
   - solver selection/fallback strategy
   - explicit compatibility matrix with tax/settlement features

These candidates should only proceed as dedicated RFCs with concrete business use-cases, acceptance criteria, and demo/test impact.

## 4. Next-Step Rule

Any future item retained from this document must be promoted to a dedicated RFC before implementation, with:
1. specific business value statement,
2. API/model contract impact,
3. deterministic test strategy,
4. demo and manual validation plan.
