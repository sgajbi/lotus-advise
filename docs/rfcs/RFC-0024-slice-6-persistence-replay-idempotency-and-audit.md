# RFC-0024 Slice 6: Persistence, Replay, Idempotency, and Audit

Status: Implemented on 2026-05-23.

## Purpose

Slice 6 makes the Slice 5 memo evidence pack durable without adding public memo APIs or product
surface support. It introduces memo persistence records, idempotency mappings, replay metadata, and
memo audit events so later API, report, Gateway, Workbench, and client-ready slices can build on
one durable source of memo truth.

This slice deliberately does not add memo routes, OpenAPI memo endpoints, report/render/archive
realization, Gateway contracts, Workbench screens, active data-product support, or client-ready memo
publication.

## Implemented Behavior

1. `src/core/proposals/persistence_models.py` defines `ProposalMemoRecord`,
   `ProposalMemoIdempotencyRecord`, and `ProposalMemoEventRecord`.
2. `src/core/proposals/memo_persistence.py` adds `create_or_replay_proposal_memo`, which builds the
   memo evidence pack from an immutable proposal version, persists one memo per proposal version,
   records idempotency mappings, and emits a memo audit event for new memo records.
3. `src/infrastructure/proposals/in_memory.py` and `src/infrastructure/proposals/postgres.py`
   implement memo persistence, memo idempotency lookup, memo listing, and memo event persistence.
4. `src/infrastructure/postgres_migrations/proposals/0007_memo_persistence.sql` adds
   `proposal_memos`, `proposal_memo_idempotency`, and `proposal_memo_events`.
5. Persisted memo records carry projection posture, review-event slots, report-package event slots,
   archive refs, AI refs, and replay metadata. These fields are intentionally empty until later
   slices implement review APIs, report packages, archive realization, and AI memo references.
6. Idempotent replay returns the existing memo for the same request hash and rejects payload drift
   with `MEMO_IDEMPOTENCY_KEY_CONFLICT`.
7. Finalization is blocked unless the memo evidence pack is fully `READY`, which keeps current
   report/render/archive blockers from becoming finalized client-ready truth.

## Design Review

The implementation keeps persistence separate from the pure Slice 5 builder. `memo_persistence.py`
is the orchestration boundary: it consumes immutable `ProposalVersionRecord` truth, calls the pure
builder, creates a durable `ProposalMemoRecord`, and writes idempotency and audit evidence through
the repository interface.

The memo tables are separate from proposal workflow events. This avoids overloading proposal
lifecycle events with memo-specific state and gives later review/report/archive slices a clear place
to attach memo events without expanding `ProposalWorkflowService`.

## Acceptance Review

| Gate | Status | Evidence |
| --- | --- | --- |
| Persist memo drafts | Pass | Unit tests create a durable `DRAFT` memo from immutable proposal-version evidence. |
| Persist replay metadata | Pass | Memo records carry proposal request, artifact, simulation, memo source-input, and memo request hashes. |
| Idempotent replay | Pass | Repeated calls with the same idempotency key and request hash return the existing memo without new audit events. |
| Payload drift rejected | Pass | Reusing a memo idempotency key with a changed proposal artifact hash raises `MEMO_IDEMPOTENCY_KEY_CONFLICT`. |
| Audit events | Pass | New memo persistence emits `MEMO_DRAFT_CREATED`; replay does not duplicate audit truth. |
| Finalized memo immutability guarded | Pass | `FINALIZED` creation is rejected while memo evidence remains `BLOCKED`. |
| Public support not promoted | Pass | No memo API route, OpenAPI endpoint, Gateway/Workbench support, or supported-feature product promotion is added. |

## Local Validation

1. `python -m pytest tests/unit/advisory/engine/test_engine_proposal_memo_persistence.py tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py::test_postgres_repository_memo_idempotency_memo_and_events_roundtrip -q`
2. `python -m ruff check src/core/proposals/persistence_models.py src/core/proposals/models.py src/core/proposals/repository.py src/core/proposals/memo_persistence.py src/infrastructure/proposals/in_memory.py src/infrastructure/proposals/postgres.py tests/unit/advisory/engine/test_engine_proposal_memo_persistence.py tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py`
3. `python -m mypy --config-file mypy.ini src/core/proposals/memo_persistence.py src/core/proposals/persistence_models.py src/core/proposals/repository.py src/infrastructure/proposals/in_memory.py src/infrastructure/proposals/postgres.py`

## Wiki And README Decision

The repo RFC index and authored wiki source are updated because this slice changes durable RFC
state. The supported-features page records Slice 6 as backend persistence foundation only. It
continues to state that memo APIs, report package, Gateway, Workbench, active data-product support,
and client-ready memo claims remain planned.

## Remaining Gates

1. Slice 7 must add certified memo APIs and OpenAPI before external consumers can read or create
   memo records.
2. Later slices must add memo review, report/render/archive realization, Gateway, Workbench, active
   data-product support, live proof, and client-ready governance before memo support can be
   promoted as a product capability.
