# RFC-0005: Advisory PostgreSQL Runtime and Persistence Cutover

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-03-25 |
| **Depends On** | RFC-0004, RFC-0006 |
| **Supersedes** | RFC-0001 |
| **Doc Location** | `docs/rfcs/RFC-0005-postgres-only-advisory-runtime-hard-cutover.md` |

## 1. Executive Summary

`lotus-advise` should converge on a single advisory runtime persistence posture:

- PostgreSQL is the only supported runtime persistence backend.
- advisory persistence is explicit, deterministic, and bank-grade across environments.
- the advisory database stores advisory-owned records only.

This RFC replaces the older split between "production-only cutover" and "later hard cutover" with
one unified target-state RFC aligned to the `RFC-0006` architecture.

## 2. Problem Statement

The current RFC set still describes persistence in an overlapping way:

- `RFC-0001` describes a transitional production-only profile policy.
- `RFC-0005` describes a later hard cutover.
- `RFC-0013` still carries MVP in-memory persistence language that is no longer the desired
  end-state.

That split made sense during transition, but it is now confusing for a gold-standard advisory app.
The service needs one clear runtime and persistence direction.

## 3. Goals

1. Make PostgreSQL the only supported runtime persistence backend for advisory service behavior.
2. Remove legacy runtime backend ambiguity from configuration, code paths, docs, and tests.
3. Keep the advisory database limited to advisory-owned data only.
4. Align runtime, migrations, startup checks, and supportability behavior with `RFC-0006`.
5. Provide a clean persistence foundation for `RFC-0013`, `RFC-0017`, and later production slices.

## 4. Non-Goals

1. Defining the full proposal workflow lifecycle domain model.
2. Moving canonical portfolio, risk, reporting, or AI data ownership into `lotus-advise`.
3. Designing external execution provider contracts.
4. Re-introducing environment-specific fallback runtime backends for convenience.

## 5. Decision

`lotus-advise` will support PostgreSQL-only runtime persistence.

This means:

1. proposal, workspace, workflow, approval, consent, and advisory audit data persist in PostgreSQL,
2. runtime configuration must fail fast unless the advisory PostgreSQL contract is satisfied,
3. no runtime fallback to `IN_MEMORY`, `SQL`, `SQLITE`, or `ENV_JSON` remains in active service
   paths,
4. the advisory database schema remains advisory-only and does not absorb ownership from other
   Lotus services.

## 6. Why RFC-0001 Is Being Superseded

`RFC-0001` captured a valid transition: production had to become PostgreSQL-only before local and
legacy runtime paths were removed.

That is now historical context, not the target policy.

The new source of truth is:

1. one runtime persistence posture,
2. one advisory-only database direction,
3. one set of rollout and guardrail expectations.

`RFC-0001` should remain as historical traceability, but not as active direction-setting guidance.

## 7. Runtime and Database Direction

### 7.1 Runtime Backend Policy

- `PROPOSAL_STORE_BACKEND` resolves to `POSTGRES` only.
- alias or fallback values for legacy backends are not accepted.
- startup fails fast with Lotus-branded reason codes when runtime persistence requirements are not
  met.

### 7.2 Advisory-Only Database Scope

The `lotus-advise` database stores only advisory-owned records.

Current implemented runtime scope includes:

1. proposal records and immutable versions,
2. workflow events,
3. approvals and consent records where present,
4. advisory execution handoff correlation records where later slices require durability,
5. advisory audit and idempotency records.

Deferred advisory persistence domains such as durable workspace session state remain advisory-owned,
but are completed through later RFC slices such as `RFC-0013` rather than by broadening runtime
scope implicitly.

The database must not become a shadow system of record for:

1. positions,
2. transactions,
3. market data,
4. risk analytics,
5. reports,
6. shared AI runtime state owned elsewhere.

### 7.3 Operational Guardrails

Required guardrails include:

1. startup validation for advisory DSN and backend policy,
2. migration smoke in CI and deployment flows,
3. startup smoke and negative guardrail tests,
4. fail-fast behavior for invalid or partial runtime persistence configuration.

## 8. Relationship to RFC-0013

`RFC-0005` owns the runtime and storage posture.

`RFC-0013` owns the advisory persistence domain model and lifecycle behavior.

Boundary:

1. `RFC-0005` answers: "what persistence runtime is allowed and how is it governed?"
2. `RFC-0013` answers: "what advisory-owned entities, events, versions, and audit records are
   persisted?"

This separation is deliberate and should remain clean.

## 9. Implementation Shape

1. Remove any remaining legacy runtime backend selection and fallback logic.
2. Keep runtime config helpers explicit and PostgreSQL-only.
3. Ensure repository wiring and service startup align to the PostgreSQL-only policy.
4. Keep migrations, smoke checks, and deployment docs aligned to the single runtime posture.
5. Tighten docs, examples, and env templates so they do not imply mixed persistence support.
6. Keep naming and directory structure advisory-first and free of stale historical scope.

## 10. Implementation Slices

### Slice 1: Always-On Advisory Postgres Runtime Contract

Outcome:
- active service startup no longer depends on a transitional `LOCAL` versus `PRODUCTION`
  persistence-profile split,
- advisory Postgres runtime validation becomes the always-on service rule,
- docs and tests stop describing mixed runtime enforcement behavior.

Implementation shape:
1. simplify runtime guardrails so active service startup always validates the advisory Postgres
   contract,
2. remove transitional runtime-profile assumptions from active runtime docs and tests,
3. keep production cutover checks focused on migration readiness rather than profile gating.

Acceptance gate:
1. service startup fails fast without advisory Postgres DSN,
2. active runtime no longer relies on `APP_PERSISTENCE_PROFILE` to decide whether Postgres is
   required,
3. docs and tests reflect always-on advisory Postgres runtime behavior.

### Slice 2: Legacy Runtime Surface Cleanup

Outcome:
- no active runtime, examples, or supportability surfaces imply legacy proposal backends remain
  available.

### Slice 3: Advisory-Only Persistence Scope Completion

Outcome:
- advisory database ownership boundaries are explicit across workspace, proposal, workflow, and
  audit persistence.

## 11. Acceptance Criteria

This RFC is complete when:

1. active runtime code no longer supports legacy persistence backends,
2. startup and CI guardrails enforce the PostgreSQL-only posture,
3. docs and examples consistently describe the advisory PostgreSQL-only runtime,
4. the advisory persistence database scope is documented as advisory-only,
5. `RFC-0001` is marked superseded in the RFC index and no longer treated as active future
   direction.

## 12. Current Reality

Current implementation status:

1. the earlier production profile cutover from `RFC-0001` is already implemented,
2. `lotus-advise` now enforces advisory Postgres runtime contract at active service startup,
3. active runtime and supportability surfaces no longer imply legacy proposal backends are valid
   service runtime choices,
4. advisory persistence boundary is explicitly documented in runtime supportability and platform
   documentation.

## 14. Implementation Notes

The active supportability surface now distinguishes:

1. advisory-owned persisted tables implemented today,
2. deferred advisory persistence domains still owned by `lotus-advise`,
3. upstream-owned data domains that must not enter the advisory database.

That distinction is intentional and keeps this RFC aligned with `RFC-0013` rather than blurring
runtime posture with later lifecycle-domain delivery.

## 13. Next Actions

1. treat this RFC as the single runtime-persistence source of truth going forward,
2. keep future proposal and workspace durability work aligned to the advisory-owned scope defined
   here,
3. implement lifecycle and audit completion through `RFC-0013`, not by reopening mixed runtime
   backend behavior.
