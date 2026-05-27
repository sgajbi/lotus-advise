# RFC-0023 to RFC-0025 Gold-Pass Audit

| Metadata | Details |
| --- | --- |
| **Status** | Complete for advisor-use narrative, memo, and policy-evidence audit scope |
| **Audit Date** | 2026-05-27 |
| **Portfolio Evidence** | `PB_SG_GLOBAL_BAL_001` |
| **Canonical Scenario** | `RFC23_25_ADVISORY_PROPOSAL_POLICY_CANONICAL` |
| **Live Evidence Marker** | `POLICY_EVALUATION_PENDING_REVIEW_CREATED` |

## 1. Audit Scope

This audit reviews RFC-0023, RFC-0024, RFC-0025, and the closed WTBD ledger for implementation
truth, test posture, Workbench/Gateway evidence, data-product boundaries, documentation posture, and
unsupported-claim controls.

The audit does not promote client-ready publication, external client communication, order
generation, OMS execution, completed policy approval/waiver authority, completed policy sign-off
authority, or full RFC-0028 bank-demo/RFP claims. Those remain gated until implemented and proved by
their owning RFCs.

## 2. Slice Verdicts

| RFC | Supported completion | Gold-pass verdict | Evidence anchor |
| --- | --- | --- | --- |
| RFC-0023 | Advisor-review proposal narrative evidence | Complete for bounded advisor-use narrative posture; client-ready narrative remains gated. | `proposal-narrative-posture-live.png`, Gateway narrative create/review/report-package path, `ProposalNarrativeEvidence:v1` posture |
| RFC-0024 | Advisor-use proposal memo and evidence pack | Complete for advisor-use memo evidence; client-ready memo publication remains gated. | `proposal-memo-evidence-pack-live.png`, Gateway memo create/replay/review/report-package path, `AdvisoryProposalMemoEvidencePack:v1` posture |
| RFC-0025 | Advisor/compliance policy evaluation evidence | Complete for policy evaluation, review queue, workflow, blocked client-ready posture, and request-more-evidence proof; completed approval/sign-off/client-ready authority remains gated. | `advisory-suitability-review-live.png`, `POLICY_EVALUATION_PENDING_REVIEW_CREATED`, `AdvisoryPolicyEvaluationRecord:v1` posture |

## 3. WTBD Verdict

`docs/rfcs/WTBD.md` is a closed historical ledger. WTBD-001, WTBD-002, WTBD-003, and WTBD-004 are
closed and imported as constraints in RFC-0023, RFC-0024, and RFC-0025. No active WTBD dependency
remains for the audited scope, and no new WTBD should be created for these RFCs. New work belongs in
the relevant RFC, owner-repository PR, acceptance criterion, or explicit blocked/removed claim.

## 4. Live Stack Proof

The canonical front-office stack was brought up for `PB_SG_GLOBAL_BAL_001`, seeded with governed
portfolio evidence, and validated through Workbench and Gateway. The first live run exposed a real
repeatability defect: `SG_PRIVATE_BANKING_REFERENCE` version `2026.05` activation returned
`POLICY_PACK_VERSION_ALREADY_ACTIVE_IMMUTABLE` on rerun. The Workbench validator now treats that
immutable already-active response as idempotent replay evidence.

The follow-on hardening run exposed and fixed two additional repeatability defects:

1. policy review queues were not portfolio-scoped end to end, so stale `PENDING_REVIEW` evaluations
   from another portfolio could satisfy a canonical queue check,
2. the front-office benchmark seed rewrote multiple benchmark definitions to the same private
   banking benchmark identity, which could fail repeatable reference-data ingest with duplicate
   conflict keys.

The hardened validator now requires `portfolio_id=PB_SG_GLOBAL_BAL_001` on the Advise record and
Gateway/Workbench queue request, rejects out-of-scope queue items, uses separate maker/checker
actors for policy-pack activation, and treats missing policy-evaluation portfolio identity as an
API validation error. The final rebuilt-image rerun passed `npm run live:stack:up:validate` and
produced machine-readable evidence in:

`lotus-workbench/output/playwright/live-canonical/live-validation-summary.json`

Critical evidence reviewed:

1. governed advisory scenario loaded from the platform canonical demo-data contract,
2. proposal narrative proof created through Gateway,
3. proposal memo evidence created, replayed, reviewed, and surfaced through Gateway,
4. policy pack version validated and activated or idempotently replayed as already active,
5. policy evaluation created for `RFC25_SG_STRUCTURED_NOTE_PENDING_REVIEW`,
6. portfolio-scoped review queue returned only the seeded `PENDING_REVIEW` policy evaluation for
   `PB_SG_GLOBAL_BAL_001`,
7. workflow and sign-off package returned blocked client-ready posture,
8. request-more-evidence decision was recorded,
9. Workbench screenshots were captured under the governed live-canonical evidence directory.

## 5. Quality Improvements Made

1. RFC-0023, RFC-0024, and RFC-0025 now carry explicit Gold-Pass Assessment sections.
2. The platform canonical demo-data contract owns the shared advisory scenario rather than hiding
   it in Workbench validator literals.
3. Workbench live validation proves real RFC-0025 policy queue behavior instead of only navigating
   to the Suitability Review route.
4. The live validator is repeatable when the policy pack is already active and immutable.
5. Policy evaluation records now require source-owned portfolio identity and review-queue
   validation is portfolio-scoped through Advise, Gateway, Workbench, and live automation.
6. The canonical Core benchmark seed now rewrites only the governed demo benchmark to the private
   banking benchmark identity, preventing duplicate benchmark-definition/composition/return-series
   keys on repeatable seeded runs.
7. Documentation and wiki source describe the bounded advisor-use/client-ready split.

## 6. Remaining Gated Claims

The audited scope is production-ready only for bounded advisor-use and advisor/compliance evidence.
The following claims remain deliberately not supported:

1. client-ready narrative publication,
2. client-ready memo publication,
3. completed policy approval or waiver authority,
4. completed compliance sign-off authority,
5. external client communication,
6. OMS/order/fill/settlement execution,
7. full RFC-0028 bank-demo/RFP package claims.

## 7. Validation Commands

Focused validation used for this audit:

1. `lotus-advise`: `python -m pytest tests/unit/advisory/api/test_api_advisory_policy_evaluations.py -q`
2. `lotus-platform`: `python -m pytest tests/unit/test_rfc_0076_canonical_demo_data_contract.py -q`
3. `lotus-workbench`: `npm test -- --run tests/unit/live-canonical-validation-script.test.ts`
4. `lotus-workbench`: `npm test -- --run tests/unit/advisory-policy-proof.test.ts`
5. `lotus-gateway`: `python -m pytest tests/contract/test_advise_gateway_route_coverage.py tests/integration/test_advisory_policy_router.py tests/unit/test_upstream_clients.py -q`
6. `lotus-core`: `python -m pytest tests/unit/tools/test_front_office_portfolio_seed.py -q`
7. `lotus-core`: `python -m pytest tests/integration/tools/test_demo_data_pack.py -q`
8. `lotus-workbench`: `npm run live:validate`
9. `lotus-workbench`: `npm run live:stack:up:validate`
10. `lotus-workbench`: `npm run live:stack:down`

## 8. Final Assessment

RFC-0023 to RFC-0025 meet the gold-pass standard for their current supported scope: advisor-review
narrative evidence, advisor-use memo evidence, and advisor/compliance policy evaluation evidence.
They should not be described as complete for client-ready publication or external communication
until the explicitly gated controls are implemented and validated by follow-on RFCs.
