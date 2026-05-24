# RFC-0024 Slice 8 - Policy, Fees, Costs, Conflicts, And Disclosures

## Implemented Behavior

Slice 8 enriches the persisted `AdvisoryProposalMemoEvidencePack:v1` memo sections for
suitability, best-interest posture, product eligibility, costs, fees, tax, execution friction,
conflicts, and disclosures.

Implemented behavior:

1. `SUITABILITY_AND_BEST_INTEREST` now includes deterministic claims for suitability issue counts
   and proposed-trade product eligibility/complexity coverage when source evidence is present.
2. `FEES_COSTS_TAX_AND_FRICTIONS` now preserves cost, fee, tax, and execution-friction limitation
   notes from the immutable proposal artifact instead of returning a generic placeholder.
3. `CONFLICTS_AND_DISCLOSURES` now preserves artifact risk-disclosure text and product-document
   references while keeping conflict-of-interest evidence review-required.
4. memo supportability now reflects the implemented Slice 6 persistence, Slice 7 API, and Slice 8
   policy/fee/conflict enrichment posture instead of the old pure-builder-only wording.

Slice 8 still does not implement full RFC-0025 policy-pack authority, tax methodology, fee
calculation, conflict-of-interest policy management, Gateway/Workbench memo surfaces,
report/render/archive realization, active data-product support, or client-ready memo publication.

## Design Review

The enrichment logic lives in `src/core/proposals/memo_policy_enrichment.py` instead of expanding
`memo_builder.py`. The builder remains responsible for section assembly and hash calculation,
while the new module owns memo-critical policy, fee, tax, conflict, and disclosure interpretation.

This keeps the implementation modular and makes later RFC-0025 policy-pack consumption easier:
future policy-pack evidence can replace or extend the enrichment module without rewriting the
section assembly pipeline.

## Acceptance Review

Slice 8 acceptance criteria:

| Criterion | Evidence |
| --- | --- |
| Consume available RFC-0025/RFC-0016-style evidence or implement the memo-critical subset | Existing source evidence is used now: artifact suitability summaries, proposal assumptions, proposal disclosures, product-document refs, and `lotus-core` shelf eligibility/complexity evidence. Missing full policy-pack evidence remains explicitly review-required. |
| Missing evidence cannot become positive suitability or best-interest wording | `tests/unit/advisory/engine/test_engine_proposal_memo_builder.py` proves fee/tax/friction and conflict sections remain `PENDING_REVIEW`, preserve missing evidence, and do not emit client-ready claims. |
| Memo APIs expose the enriched persisted evidence | `tests/unit/advisory/api/test_api_advisory_proposal_memo.py` verifies persisted memo supportability reflects Slice 6/7/8 implementation truth. |

## Current Product Boundary

Supported now:

1. memo-critical suitability issue count evidence,
2. proposed-trade product eligibility/complexity coverage evidence,
3. cost, fee, tax, and execution-friction limitation evidence,
4. risk-disclosure and product-document reference evidence,
5. review-required conflict posture when conflict policy-pack evidence is absent.

Still not supported:

1. full suitability and best-interest policy-pack authority,
2. fee, cost, tax, or execution-friction calculation methodology,
3. conflict-of-interest policy management or positive conflict clearance,
4. Gateway or Workbench memo product surfaces,
5. report/render/archive realization,
6. active `AdvisoryProposalMemoEvidencePack:v1` data-product support,
7. client-ready memo approval, publication, or external client communication.

## Wiki And README Decision

Repo-local wiki source and RFC index are updated because Slice 8 changes current memo feature truth.
README remains unchanged because command, install, and repository orientation truth is unchanged.

## Remaining Gates

Later RFC-0024 slices still need report/render/archive realization, AI narrative integration,
Gateway/Workbench product realization, live front-office proof, commercial/demo material,
hardening review, final closure, and post-completion communication before RFC-0024 can be marked
fully implemented.
