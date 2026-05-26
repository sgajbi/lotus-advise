# RFC-0025 Slice 7 - Policy Evaluation Persistence, Replay, Idempotency, And Audit

Status: IMPLEMENTED - INTERNAL PERSISTENCE AND REPLAY ONLY; NO API OR PRODUCT SURFACE PROMOTED

## Scope Boundary

This slice persists finalized internal policy evaluation truth for `lotus-advise`.
It builds on Slice 6 and records the evaluated policy pack, policy version, source evidence hash,
rule result hashes, source refs, source gaps, approval dependencies, disclosure requirements,
consent requirements, replay metadata, and append-only audit events.

This slice does not implement certified policy evaluation APIs, review queues, compliance sign-off
workflow, report/render/archive materialization, Gateway consumption, Workbench consumption, AI
policy-evidence packets, active data-product promotion, or client-ready publication. Those remain
later RFC-0025 slices.

## Implementation

The persistence boundary lives in `src/core/policy_packs/persistence.py` and uses contract
`rfc0025.policy-evaluation-persistence.v1`.

Implemented behavior:

1. finalized `PolicyEvaluationRecord` storage keyed by proposal, proposal version, policy pack,
   policy version, and source evidence hash,
2. canonical `source_evidence_hash`, `policy_content_hash`, aggregate `evaluation_hash`, and
   per-rule result hashes,
3. duplicate request prevention for the same finalized evaluation identity,
4. idempotent finalize command replay and conflict rejection when the same key is reused for a
   different payload,
5. append-only review, sign-off, and report/archive reference events,
6. replay comparison that pins the stored policy version, compares current policy content hash,
   compares source evidence hash, and compares replayed evaluation hash,
7. persisted disclosure, consent, and approval dependency projections derived from source-backed
   rule outcomes.

The Slice 6 evaluator supportability now reports
`policy_evaluation_persistence = SUPPORTED_BY_RFC0025_SLICE7_INTERNAL` while keeping
`policy_evaluation_api`, Gateway, Workbench, and client-ready publication blocked.

## Data Product Posture

`AdvisoryPolicyEvaluationRecord:v1` remains a proposed and blocked data product after this slice.
The blocking reason narrows from missing persistence and API support to missing certified APIs,
review/sign-off workflows, downstream package realization, Gateway/Workbench consumption, live
proof, and final supportability promotion.

This is intentional: internal persistence is necessary for the data product, but it is not enough
to expose or market policy evaluation as a supported product surface.

## Acceptance Evidence

Tests:

1. `tests/unit/advisory/engine/test_engine_policy_pack_persistence.py`
2. `tests/unit/advisory/engine/test_engine_policy_pack_evaluation.py`
3. `tests/unit/advisory/engine/test_engine_policy_pack_catalog.py`
4. `tests/unit/test_rfc0025_slice7_policy_evaluation_persistence_contract.py`

Covered paths:

1. finalized records are immutable and hash-backed,
2. duplicate finalized evaluation requests do not create duplicate records,
3. idempotency key reuse with payload drift is rejected,
4. review, sign-off, and report/archive refs are append-only events,
5. event replay does not mutate finalized evaluation hash,
6. replay exposes stored versus replayed policy, source, and evaluation hashes,
7. complex-product policy outcomes persist disclosure, consent, and approval dependencies.

## Wiki And README Decision

Repo README/RFC index, repo context, codebase review ledger, trust telemetry, data-product
declaration posture, and wiki source are updated because implementation truth changed. Wiki
publication is required after merge.
