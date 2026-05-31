# RFC-0027 Slices 10-14 - Product Realization, Data Mesh, Proof, and Closure

Status: IMPLEMENTED - GOVERNED ADVISORY COPILOT SUPPORTED FOR INTERNAL ADVISOR/REVIEWER USE

## Outcome

Slices 10-14 close RFC-0027 across Gateway, Workbench, canonical automation, data mesh, and durable
documentation truth.

Implemented scope:

1. Gateway publishes `/api/v1/advisory-copilot/*` routes that proxy only to Advise-owned copilot
   APIs and do not call `lotus-ai` directly.
2. Workbench renders `/recommendations?mode=copilot` through the Gateway BFF only.
3. Canonical automation proves `RFC27_ADVISORY_COPILOT_CANONICAL` for `PB_SG_GLOBAL_BAL_001`.
4. The proof creates source-backed proposal-version evidence packets for all six supported action
   families, executes governed copilot actions, records internal review, proves client-ready
   guardrail rejection, and verifies proposal-version run lineage.
5. `AdvisoryCopilotInteractionRecord:v1` is promoted as an active data product for reviewed
   internal advisor/reviewer copilot interactions.
6. Evidence packets and review events remain audit records within the interaction product boundary;
   they are not promoted as standalone data products.

## Capability Boundary

Supported:

1. proposal explanation,
2. bounded evidence Q&A,
3. advisor meeting preparation,
4. compliance review summary,
5. operations/report handoff summary,
6. advisor-reviewed client follow-up draft,
7. source refs, lineage, hashes, guardrail posture, unavailable/degraded posture, and internal
   review posture.

Blocked:

1. client-ready publication,
2. external client communication delivery,
3. policy approval or sign-off authority,
4. OMS order lifecycle, fills, settlement, and execution,
5. full RFC-0028 bank-demo/RFP package claims.

## Data Mesh Closure

`AdvisoryCopilotInteractionRecord:v1` is declared in
`contracts/domain-data-products/lotus-advise-products.v1.json` and covered by
`contracts/trust-telemetry/advisory-copilot-interaction-record.telemetry.v1.json`.

The active product is bounded to source-backed, reviewed, internal advisor/reviewer support. It
requires `product_name`, `product_version`, `generated_at`, `content_hash`, and `correlation_id`
trust metadata, materialized lineage, and customer-consumable evidence access. Approved consumers
are `lotus-gateway` and `lotus-workbench`.

## Live Evidence

Canonical Workbench validation passed on 2026-05-28 for `PB_SG_GLOBAL_BAL_001`.

Evidence:

1. marker: `ADVISORY_COPILOT_CANONICAL_PROOF_CREATED`,
2. scenario: `RFC27_ADVISORY_COPILOT_CANONICAL`,
3. panel: `advisory.advisory_copilot`,
4. action families: `PROPOSAL_EXPLANATION`, `EVIDENCE_QA`, `MEETING_PREPARATION`,
   `COMPLIANCE_REVIEW_SUMMARY`, `OPERATIONS_REPORT_HANDOFF`, `CLIENT_FOLLOW_UP_DRAFT`,
5. review posture: `APPROVED_FOR_INTERNAL_USE` after internal review,
6. client-ready publication: `BLOCKED`,
7. guardrail posture: `GUARDRAIL_REJECTED`,
8. screenshot: `lotus-workbench/output/playwright/live-canonical/advisory-advisory-copilot-live.png`,
9. summary: `lotus-workbench/output/playwright/live-canonical/live-validation-summary.json`.

## Repeatability Hardening

Live validation exposed and fixed these repeatability gaps:

1. stale transient `UNAVAILABLE` action runs are refreshed after dependency recovery,
2. safe blocked client-ready boundary language is not falsely rejected by output guardrails,
3. proposal-version lineage is preserved for action families whose evidence sections do not include
   proposal context text,
4. source-projected evidence packets refresh when the same proposal version projection changes hash,
5. Workbench action/guardrail idempotency keys include evidence-packet hash,
6. Workbench live selector assertions use accessible labels rather than ambiguous business copy,
7. canonical proof executions include a per-run execution id so previously reviewed runs cannot be
   replayed as fresh review-required runs.

Each runtime gap is covered by targeted unit tests in the owning repository.

## Closure

RFC-0027 is implemented for governed internal advisor/reviewer copilot interactions. The closure
does not promote client-ready advice, client communication delivery, policy approval/sign-off,
order management, fills, settlement, or RFC-0028 demo/RFP readiness.
