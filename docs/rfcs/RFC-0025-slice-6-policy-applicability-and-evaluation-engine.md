# RFC-0025 Slice 6 - Policy Applicability And Evaluation Engine

Status: IMPLEMENTED - INTERNAL EVALUATION ENGINE ONLY; NO PERSISTENCE OR API PROMOTED

## Scope Boundary

This slice implements the first internal RFC-0025 policy evaluation engine in `lotus-advise`.
It evaluates an active policy-pack version against source-backed proposal evidence and returns
material rule results with source refs, missing evidence, reason codes, and required actions.

This slice does not implement persisted policy evaluation records, replay, idempotent evaluation
commands, review queues, sign-off packages, certified policy evaluation APIs, Gateway consumption,
Workbench consumption, report/render/archive policy packages, AI policy packets, or client-ready
publication. In short: no persistence/API/product-surface promotion is claimed by this slice.

## Implementation

The engine lives in `src/core/policy_packs/evaluation.py` and uses contract
`rfc0025.policy-evaluation-engine.v1`.

Implemented behavior:

1. active policy-pack enforcement before evaluation,
2. source-backed applicability for jurisdiction, booking center, and client segment,
3. global baseline source-readiness and mandate-restriction review,
4. Singapore reference product eligibility and target-market review,
5. complex/private/structured product disclosure and consent review posture,
6. best-interest cost, fee, tax, and execution-friction evidence posture,
7. conflict and product-document review posture,
8. degraded and missing source-owner evidence handling through
   `rfc0025.policy-source-readiness.v1`,
9. material outcomes that avoid generic pass/fail or unsupported client-ready wording.

Slice 5 catalog definitions now include first-wave evaluation rules for:

1. `GLOBAL_SOURCE_READINESS_REQUIRED`,
2. `GLOBAL_MANDATE_RESTRICTIONS_REVIEW`,
3. `SG_AI_PRODUCT_ELIGIBILITY_REVIEW`,
4. `SG_COMPLEX_PRODUCT_DISCLOSURE_REVIEW`,
5. `SG_BEST_INTEREST_COST_REVIEW`,
6. `SG_CONFLICT_REVIEW`.

## Source-Readiness Update

`src/core/proposals/policy_source_readiness.py` now reflects that an internal evaluator exists:

1. `capability_posture` is `SOURCE_READINESS_WITH_INTERNAL_POLICY_EVALUATION_ENGINE`,
2. `claim_policy.policy_evaluation` is `INTERNAL_ENGINE_ONLY_NO_PERSISTED_API`,
3. `advise_policy_evaluation_runtime` is `READY`,
4. degraded `lotus-risk` source evidence remains `PENDING_REVIEW`.

This keeps source-owner evidence truthful without claiming durable policy evaluation records or
front-office product support before later slices implement them.

## Acceptance Evidence

Tests:

1. `tests/unit/advisory/engine/test_engine_policy_pack_evaluation.py`
2. `tests/unit/advisory/engine/test_engine_policy_source_readiness.py`
3. `tests/unit/test_rfc0025_slice6_policy_evaluation_contract.py`

Covered paths:

1. ready active-pack evaluation,
2. non-active policy-pack rejection,
3. missing source-owner evidence blocked posture,
4. degraded source-owner evidence pending-review posture,
5. jurisdiction applicability,
6. client-segment missing evidence,
7. mandate source readiness,
8. product eligibility and target-market blocking,
9. complex product disclosure and consent required actions,
10. best-interest cost/tax/friction pending review,
11. conflict and product-document pending review,
12. material conflict blocked posture.

## Wiki And README Decision

Repo README/RFC index, repo context, codebase review ledger, and wiki source are updated because
implementation truth changed. Wiki publication is required after merge.
