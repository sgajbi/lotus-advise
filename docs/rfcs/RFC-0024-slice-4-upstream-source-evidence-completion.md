# RFC-0024 Slice 4: Upstream Source Evidence Completion

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0024: Advisor Proposal Memo and Evidence Pack |
| **Slice** | 4 - upstream source evidence completion |
| **Status** | IMPLEMENTED - SOURCE-READINESS ONLY; NO MEMO SUPPORT PROMOTED |
| **Implemented Date** | 2026-05-23 |
| **Owner** | `lotus-advise` source-readiness projection over source-owned evidence |
| **Implementation Branch** | `rfc0024-slice4-upstream-source-evidence` |
| **Capability Posture** | This slice adds persisted memo source-readiness evidence to proposal-version evidence bundles. It does not implement advisor proposal memo generation, memo APIs, memo persistence, memo report packages, Gateway/Workbench memo surfaces, or client-ready memo publication. |

## Decision

Slice 4 implements the first RFC-0024 source-authority control in `lotus-advise` without moving
source methodology out of the owning services.

Every persisted proposal evidence bundle now includes `memo_source_readiness`, a deterministic
source-authority manifest with:

1. contract version `rfc0024.memo-source-readiness.v1`,
2. owner-service attribution for `lotus-core`, `lotus-risk`, and `lotus-advise`,
3. readiness statuses `READY`, `PENDING_REVIEW`, `BLOCKED`, and `NOT_AVAILABLE`,
4. evidence refs for each memo-critical source family,
5. missing-evidence names and reason codes,
6. an explicit claim policy that keeps memo generation `NOT_IMPLEMENTED` and client-ready
   publication `BLOCKED`.

This lets future memo domain builders consume source-readiness truth from stored proposal evidence
instead of re-reading source systems or inventing missing facts.

## Source Evidence Boundary

| Source family | Owner | Slice 4 behavior |
| --- | --- | --- |
| Portfolio holdings and cash | `lotus-core` | Ready only when the proposal evidence came through `LOTUS_CORE` context resolution and contains positions and cash balances. Direct/stateless input is `PENDING_REVIEW` or `BLOCKED`, not source-owned truth. |
| Household, account, mandate, objectives, restrictions | `lotus-core` | Household and mandate selectors are consumed when present. Account, objective, and restriction evidence remain explicit blockers until source-owned fields are available. |
| Prices and FX rates | `lotus-core` | Rows are consumed only as source evidence. Open-ended validity is expected as `31-Dec-3999` / `3999-12-31`; missing open-end dates produce `PENDING_REVIEW` so later memo sections cannot treat last price or FX as durable current truth. |
| Product eligibility and complexity | `lotus-core` | Product shelf evidence is ready only when eligibility and complexity attributes exist for traded instruments. Missing product shelf evidence blocks positive product-suitability claims. |
| Concentration risk | `lotus-risk` | `lotus-risk` single-position and issuer concentration evidence is marked ready when present in the risk lens. |
| Drawdown, stress, liquidity, private assets, climate/geopolitical | `lotus-risk` | Remains `PENDING_REVIEW` until source-owned evidence is available. Advise does not duplicate the risk methodology. |
| Decision summary, alternatives, lifecycle, execution boundary | `lotus-advise` | Consumes existing proposal-result evidence and marks missing alternatives or gate evidence explicitly. |

## Implementation

| Area | Change |
| --- | --- |
| Core projection | Added `src/core/proposals/memo_source_readiness.py` as a pure projection over persisted proposal evidence. |
| Evidence persistence | `build_proposal_evidence_bundle(...)` now adds `memo_source_readiness` before proposal versions are persisted. |
| Source ownership | The projection reads existing context resolution, artifact input evidence, proposal-result evidence, and optional `lotus-risk` risk lens; it does not call upstream services or implement source-owner methodology locally. |
| Unsupported fact handling | Missing source facts become `PENDING_REVIEW`, `BLOCKED`, or `NOT_AVAILABLE` with reason codes and evidence refs. |
| Memo support posture | No memo routes, persistence model, data-product promotion, Gateway/Workbench support, or `/platform/capabilities` row is added. |

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Stranded-truth reconciliation | `git fetch origin --prune` and `git branch -r --no-merged origin/main` returned no unmerged remote branches before Slice 4 implementation. |
| Source-authority projection | `tests/unit/advisory/engine/test_engine_memo_source_readiness.py` proves source-backed ready families, missing owner evidence blockers, and open-ended price/FX validity handling. |
| Persisted evidence integration | `tests/unit/advisory/engine/test_engine_proposal_evidence.py` proves persisted evidence bundles include the RFC-0024 readiness contract without memo capability promotion. |
| Open-ended market data posture | Unit coverage asserts missing price/FX validity end `31-Dec-3999` creates `PENDING_REVIEW`, matching the private-banking expectation that current market data stays open-ended until superseded. |
| Cross-repo decision | No `lotus-core` or `lotus-risk` source-owner PR is required in this slice because the current supported outcome is explicit readiness/blocker truth, not positive memo claims over missing fields. Future slices may add source-owner fields where they are needed for supported memo sections. |

## Wiki And README Decision

Wiki source is updated because RFC implementation status and supported-feature posture changed.
README does not change in this slice because runtime commands, public APIs, and supported product
entrypoints did not change.
