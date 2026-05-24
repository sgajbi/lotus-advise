# RFC-0024 Slice 10: AI Narrative and Review-Gated Commentary

## Status

Implemented for advisor-use, review-gated memo commentary.

Client-ready memo commentary, Gateway exposure, Workbench exposure, active
`AdvisoryProposalMemoEvidencePack:v1` data-product promotion, and commercial/demo claims remain
gated later RFC-0024 scope.

## Implemented Behavior

Slice 10 adds a bounded AI commentary path for persisted advisor proposal memos:

1. `lotus-ai` registers and executes `proposal_memo_commentary.pack@v1` as a review-gated workflow
   pack owned by `lotus-advise`.
2. `lotus-advise` exposes
   `POST /advisory/proposals/{proposal_id}/versions/{version_no}/memo/ai-commentary`.
3. The Advise command requires exact `source_memo_hash` continuity and a prior
   `APPROVE_FOR_ADVISOR_USE` memo review event.
4. Advise sends only a bounded memo evidence packet, requested section keys, reason metadata, and
   supportability constraints to `lotus-ai`.
5. AI output is recorded as append-only `MEMO_AI_REFERENCE_RECORDED` lineage and remains
   `REVIEW_REQUIRED`.
6. AI unavailability records deterministic `UNAVAILABLE` commentary posture with fallback lineage
   instead of mutating memo evidence or failing into guessed wording.
7. AI output cannot change memo status, memo evidence, suitability, product eligibility,
   best-interest, approval posture, report/archive posture, or client-ready publication state.

## Design Review

The slice deliberately keeps AI downstream of persisted memo evidence and review posture. Advise
remains the workflow authority for memo lifecycle, review, hash continuity, and product boundaries.
`lotus-ai` owns workflow-pack registration, execution, run-ledger posture, queue policy, safety
posture, and deterministic stub behavior.

The integration uses the existing workflow-pack execution route rather than introducing a bespoke
AI endpoint. This keeps prompt/runtime governance in `lotus-ai` while avoiding any transfer of
advisory decision authority.

## Acceptance Review

Implementation evidence:

1. `src/core/proposals/memo_api.py`
2. `src/api/proposals/routes_memo.py`
3. `src/integrations/lotus_ai/proposal_memo.py`
4. `../lotus-ai/src/app/services/workflow_pack_phase1_specs.py`
5. `../lotus-ai/src/app/services/workflow_pack_registry_seed.py`
6. `../lotus-ai/src/app/services/workflow_pack_bindings.py`
7. `../lotus-ai/src/app/services/workflow_pack_queue_policy_catalog.py`
8. `../lotus-ai/src/app/providers/proposal_memo_commentary_stub.py`
9. `tests/unit/advisory/api/test_api_advisory_proposal_memo.py`
10. `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py`
11. `../lotus-ai/tests/unit/test_workflow_pack_registry.py`
12. `../lotus-ai/tests/unit/test_workflow_pack_runtime_status.py`
13. `../lotus-ai/tests/unit/test_ai_surface_supportability.py`

## API Boundary

The new route is an advisor-use commentary request, not a memo publication route. It rejects stale
memo hashes, requires advisor-use review, supports idempotent replay, and returns commentary
posture plus AI lineage without changing the persisted memo payload.

Deterministic unavailable behavior is part of the contract: missing or unavailable `LOTUS_AI_BASE_URL`
returns a recorded `UNAVAILABLE` commentary payload with fallback lineage and review guidance.

## Wiki And README Decision

Repo-local wiki source is updated because supported-feature and RFC-index truth changed. README does
not need a separate change for this slice because the public entrypoint is already covered by the
RFC index and Supported Features page.

`lotus-ai` README and repo context are updated in the coordinated Slice 10 branch because executable
workflow-pack scope changed there.

## Remaining Gates

Slice 10 does not promote:

1. client-ready memo commentary,
2. Gateway memo product APIs,
3. Workbench memo UI,
4. active `AdvisoryProposalMemoEvidencePack:v1` data-product support,
5. commercial/demo/RFP claims,
6. final RFC-0024 closure.
