# RFC-0025 Slice 11 - AI Policy-Evidence Consumption Boundary

Status: IMPLEMENTED - ADVISE AI EVIDENCE BOUNDARY ONLY; GATEWAY, WORKBENCH, LIVE PROOF, ACTIVE DATA-PRODUCT PROMOTION, AND CLIENT-READY PUBLICATION REMAIN GATED

## Scope Boundary

This slice lets `lotus-advise` send bounded policy evidence to `lotus-ai` for review-gated
advisor/compliance explanation. It does not let AI approve, waive, mutate, certify, or publish any
policy outcome.

Implemented scope:

1. finalized policy evaluation AI-evidence request API,
2. source-hash validation against the immutable evaluation record,
3. requested-action allowlist with forbidden-action rejection,
4. redacted policy evidence packet construction,
5. `lotus-ai` workflow-pack handoff through `policy_evidence_summary.pack@v1`,
6. deterministic unavailable posture when `lotus-ai` is not configured or unavailable,
7. append-only `POLICY_EVALUATION_AI_EVIDENCE_RECORDED` lineage events,
8. replay-safe idempotency,
9. explicit human-review, non-authoritative, and client-ready blocked posture.

This slice does not implement Gateway routes, Workbench policy screens, active mesh publication,
canonical front-office proof, or external client communication.

## Implementation

The policy AI boundary lives in `src/core/policy_packs/ai.py`.

Canonical route added to `src/api/proposals/routes_policy_evaluations.py`:

1. `POST /advisory/policy-evaluations/{evaluation_id}/ai-evidence`

The `lotus-ai` adapter lives in `src/integrations/lotus_ai/policy_evidence.py` and submits
structured context to `/platform/workflow-packs/execute` with:

1. `pack_id = policy_evidence_summary.pack`,
2. `version = v1`,
3. `workflow_surface = policy-evidence-summary`,
4. `expected_output_label = EXPLANATION_ONLY`.

The evidence packet includes policy status, material rule statuses, reason codes, source refs,
source gaps, workflow posture, and append-only event summaries. It does not include the raw source
evidence bundle, raw client identity, free-text notes, or full position payload.

## Guardrails

Supported requested actions are:

1. `SUMMARIZE_POLICY_POSTURE`,
2. `EXPLAIN_OPEN_REQUIREMENTS`,
3. `EXPLAIN_SIGN_OFF_EVIDENCE`,
4. `EXPLAIN_DISCLOSURE_AND_CONSENT_POSTURE`,
5. `EXPLAIN_SOURCE_GAPS`.

The service rejects unsupported or forbidden actions, including approval, waiver, mutation,
certification, publication, and client-ready release requests.

Every AI evidence event records:

1. `rfc0025.policy-ai-evidence-boundary.v1`,
2. policy AI request hash,
3. source evaluation hash,
4. requested actions,
5. redaction profile,
6. prompt/output lineage from `lotus-ai` where available,
7. human review required,
8. authoritative-for-policy-status false,
9. client-ready publication blocked.

AI output cannot change policy status, rule results, approvals, waivers, disclosures, consent
posture, sign-off posture, report refs, or client-ready publication posture.

## Data Product Posture

`AdvisoryPolicyEvaluationRecord:v1` remains proposed and blocked after this slice.

The product now has Advise-local AI evidence consumption for policy explanations. It remains blocked
because Gateway/Workbench policy consumption, canonical live proof, supportability promotion, active
data-product promotion, and client-ready publication are not implemented. `/platform/capabilities`
must not advertise policy evaluation support until the product surface is implementation-backed.

## Acceptance Evidence

Tests:

1. `tests/unit/advisory/api/test_api_advisory_policy_evaluations.py`
2. `tests/unit/advisory/api/test_lotus_ai_policy_evidence.py`
3. `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py`
4. `tests/unit/test_rfc0025_slice11_policy_ai_evidence_contract.py`
5. `tests/unit/test_trust_telemetry.py`
6. `tests/unit/test_rfc0025_slice3_data_product_contract.py`

Covered paths:

1. bounded AI evidence requests record append-only lineage,
2. AI receives redacted policy packets rather than raw source evidence,
3. forbidden actions and stale hashes are rejected,
4. AI unavailable posture is deterministic and non-authoritative,
5. idempotent replays do not call the adapter again,
6. OpenAPI docs expose route, request/response contracts, idempotency header, and error posture,
7. data-product and trust telemetry posture remains proposed/blocked rather than promoted.

## Wiki And README Decision

Repo RFC index, repo context, codebase review ledger, data-product declaration, trust telemetry, API
vocabulary, and wiki source are updated because implementation truth changed. Wiki publication is
required after merge.
