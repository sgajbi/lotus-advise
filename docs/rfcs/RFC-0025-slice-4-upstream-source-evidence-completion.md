# RFC-0025 Slice 4: Upstream Source Evidence Completion

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0025: Enterprise Suitability and Best-Interest Policy Packs |
| **Slice** | 4 - upstream source evidence completion |
| **Status** | IMPLEMENTED - SOURCE-READINESS ONLY; NO POLICY EVALUATION PROMOTED |
| **Implemented Date** | 2026-05-26 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc25-slice4-policy-source-readiness` |
| **Capability Posture** | Proposal evidence bundles now carry `rfc0025.policy-source-readiness.v1`, a deterministic source-owner readiness manifest. This is not policy evaluation, policy-pack activation, policy persistence, Gateway/Workbench policy support, or client-ready publication. |

## Source Evidence Boundary

Slice 4 does not build the RFC-0025 policy engine. It creates the source-readiness boundary that
future policy evaluation must consume. The boundary protects product truth:

1. `lotus-core` remains the source owner for client, household, account, mandate, booking center,
   classification, objective, restriction, liquidity, time-horizon, product, price, FX, holdings,
   and cash evidence,
2. `lotus-risk` remains the source owner for concentration, drawdown, VaR, stress, liquidity-risk,
   private-asset risk, and climate/geopolitical risk evidence,
3. `lotus-advise` records only the policy-evaluation runtime gap until policy catalog, evaluation,
   persistence, replay, review, sign-off, Gateway, and Workbench slices are implemented.

Missing source-owner evidence is represented as `PENDING_REVIEW` or `BLOCKED`; it is never
defaulted into suitable, eligible, best-interest, disclosure-ready, consent-ready, or client-ready
truth.

## Implementation

This slice adds `src/core/proposals/policy_source_readiness.py`, which projects source readiness
from the existing proposal evidence bundle:

1. `core_client_profile_classification`,
2. `core_mandate_objectives_restrictions`,
3. `core_holdings_cash_market_data`,
4. `core_product_eligibility_target_market_complexity`,
5. `risk_policy_metrics`,
6. `advise_policy_evaluation_runtime`.

The existing memo readiness helpers were simplified through
`src/core/proposals/source_readiness_common.py`, so memo and policy readiness use the same section,
overall-posture, and source-authority primitives instead of duplicating that scaffolding.

`src/core/proposals/evidence.py` now attaches `policy_source_readiness` beside
`memo_source_readiness` when proposal evidence is materialized.

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Source owner boundary | `policy_source_readiness` separates `lotus-core`, `lotus-risk`, and `lotus-advise` sections and does not duplicate source methodology. |
| Missing evidence posture | Tests prove missing client/mandate, positions, prices, product shelf, and risk authority become `BLOCKED`; partial owner evidence becomes `PENDING_REVIEW`. |
| Non-claiming behavior | The manifest reports `SOURCE_READINESS_ONLY_POLICY_EVALUATION_NOT_IMPLEMENTED`, `policy_evaluation = NOT_IMPLEMENTED`, and `client_ready_publication = BLOCKED`. |
| Evidence persistence | `build_proposal_evidence_bundle` attaches `rfc0025.policy-source-readiness.v1` to persisted proposal evidence. |
| Cleanup | Shared readiness primitives remove duplicated section/posture/source-authority logic from RFC-0024 memo readiness. |

## Wiki And README Decision

Wiki source is updated because supported-feature and RFC status changed. README does not change in
this slice because no runtime command, endpoint, operator setup, or supported API entrypoint
changed.
