# RFC-0001: PostgreSQL-Only Production Mode Cutover

| Metadata | Details |
| --- | --- |
| **Status** | COMPLETED |
| **Created** | 2026-02-20 |
| **Depends On** | - |
| **Doc Location** | `docs/rfcs/RFC-0001-postgres-only-production-mode-cutover.md` |

## 1. Executive Summary

Define a staged production cutover plan where advisory persistence uses PostgreSQL-only backends in
non-dev environments, while preserving a lighter local profile where explicitly allowed.

## 2. Problem Statement

Multiple persistence modes remain available in all environments. This increases operational
variance and incident complexity in production.

## 3. Goals and Non-Goals

### 3.1 Goals

- Enforce Postgres-only persistence in production profiles.
- Preserve local development ergonomics where active advisory workflows still require them.
- Provide explicit rollout gates and fail-fast guardrails.

### 3.2 Non-Goals

- Remove all local developer convenience backends immediately.
- Change public advisory API contracts.

## 4. Proposed Design

### 4.1 Environment Policy

- Add runtime mode switch:
  - `APP_PERSISTENCE_PROFILE` (`LOCAL` | `PRODUCTION`)
- In `PRODUCTION`:
  - `PROPOSAL_STORE_BACKEND` must be `POSTGRES`
  - advisory Postgres DSN must be configured

### 4.2 Guardrails

- Startup validation fails fast with explicit reason codes when policy is violated.
- Migration checks and advisory lock controls remain mandatory for production cutover.

### 4.3 Rollout Strategy

1. Shadow validation in CI and non-prod.
2. Enable `APP_PERSISTENCE_PROFILE=PRODUCTION` in non-prod.
3. Cut over production once error budgets remain healthy.
4. Keep `LOCAL` profile as default in local/dev docs until a stricter hard-cutover RFC lands.

## 5. Test Plan

- Unit tests for persistence-profile guardrails.
- API startup tests for explicit failure reason codes.
- CI profile running with production mode plus Postgres migration smoke.

## 6. Rollout/Compatibility

- Additive and profile-gated.
- No external advisory API behavior changes.
- Local dev profile remains available until stricter cleanup is complete.

## 7. Status and Reason Code Conventions

- Startup reason codes:
  - `PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES`
  - `PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN`

## 8. Implementation Progress

- Production profile guardrails were added for advisory Postgres runtime.
- CI startup smoke and migration validation were added for production profile.
- Deployment docs were updated with explicit `LOCAL` versus `PRODUCTION` behavior.
- Later cleanup RFCs can tighten or remove remaining non-production persistence paths once advisory
  scope is fully stabilized.

