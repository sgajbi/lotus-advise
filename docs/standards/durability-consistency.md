# Durability and Consistency Standard (lotus-advise)

- Standard reference: `lotus-platform/Durability and Consistency Standard.md`
- Scope: advisory proposal simulation, proposal lifecycle, and advisory persistence write operations.
- Change control: RFC required for policy changes; ADR required for temporary exceptions.

## Workflow Consistency Classification

- Strong consistency:
  - proposal lifecycle writes
  - idempotency mapping persistence
- Eventual consistency:
  - asynchronous advisory operation fetch paths

## Idempotency and Replay Protection

- Critical write APIs require `Idempotency-Key`.
- Idempotency mapping/history repositories prevent duplicate business effects on retries.
- Evidence:
  - `src/api/routers/advisory_simulation.py`
  - `src/api/proposals/routes_lifecycle.py`
  - `src/infrastructure/proposals/postgres.py`

## Atomicity and Transaction Boundaries

- Run/proposal persistence uses explicit transaction boundaries in repository implementations.
- Proposal create persistence writes the proposal aggregate, immutable version 1, `CREATED`
  workflow event, and proposal-create idempotency record in one adapter-owned unit of work.
- Memo create persistence writes the memo record, optional memo-create idempotency record, and
  initial memo lifecycle event in one adapter-owned unit of work.
- Partial workflow updates must fail and surface explicit errors.
- Evidence:
  - `src/infrastructure/proposals/postgres.py`
  - `tests/integration/advisory/engine/test_engine_proposal_repository_postgres_integration.py`

## As-Of and Reproducibility Semantics

- Request and response contracts preserve deterministic input scope and reproducibility metadata.
- Evidence:
  - `src/core/proposals/models.py`
  - `src/core/advisory/artifact.py`

## Concurrency and Conflict Policy

- Idempotency conflict behavior is explicit (same key + different payload -> conflict).
- Workflow action conflicts are exposed through deterministic API responses.
- Repeated proposal version, workflow event, and approval identities are append-only at repository
  level: same persisted content is replay-safe, and same identity with different content raises an
  explicit identity-conflict error instead of rewriting lifecycle evidence.
- Evidence:
  - `src/core/advisory_engine.py`
  - `src/core/proposals/service.py`
  - `src/infrastructure/proposals/postgres_versions.py`
  - `src/infrastructure/proposals/postgres_workflow_events.py`
  - `src/infrastructure/proposals/postgres_approvals.py`
  - `tests/unit/core/*`

## Integrity Constraints

- Persistent stores enforce unique key constraints for run and idempotency entities.
- Proposal lifecycle persistence validates relational ownership in PostgreSQL before new
  lifecycle-integrity constraints are enabled: proposal versions must reference an existing
  proposal, externally referenced `proposal_version_id` values are unique, workflow events and
  approvals must reference the owning proposal and related version when supplied, version numbers
  must be positive, and lifecycle state/event/approval vocabularies are bounded by named check
  constraints.
- Input contracts enforce schema validation at API boundary.
- Evidence:
  - `src/infrastructure/postgres_migrations/proposals/0010_proposal_lifecycle_integrity.sql`
  - `src/core/*/models.py`

## Release-Gate Tests

- Unit: `tests/unit/*`
- Integration: `tests/integration/*`
- E2E: `tests/e2e/*`

## Deviations

- Deviation from idempotent write semantics or durable workflow persistence requires ADR with expiry review date.
