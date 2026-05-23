# RFC-0024 Slice 1: Platform Automation and Scaffolding Review

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0024: Advisor Proposal Memo and Evidence Pack |
| **Slice** | 1 - platform automation and scaffolding improvement |
| **Status** | IMPLEMENTED - REVIEWED; NO PLATFORM CHANGE REQUIRED BEFORE MEMO DOMAIN WORK |
| **Implemented Date** | 2026-05-23 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0024-slice1-platform-scaffolding` |
| **Capability Posture** | This slice does not implement advisor proposal memo generation, memo APIs, memo persistence, memo report packages, data-product promotion, Gateway/Workbench memo surfaces, or client-ready memo publication. It proves RFC-0024 can proceed using existing platform controls and defines the memo-specific controls that later implementation slices must satisfy. |

## Decision

No `lotus-platform` code or automation change is required before RFC-0024 proceeds to cleanup,
domain-model, API, data-product, report, Gateway, Workbench, and proof slices.

The review found that current Lotus platform and repo-native automation already provide the reusable
governance controls needed for the first advisor proposal memo implementation wave:

1. API certification and Swagger/OpenAPI quality gates,
2. API vocabulary and no-alias governance,
3. bounded health, readiness, capabilities, and dependency supportability posture,
4. structured logging, correlation, problem-details, and production guardrail expectations,
5. unit, integration, e2e, migration, Docker, and production-profile CI lanes,
6. domain-data-product onboarding, trust telemetry, SLO, access, evidence policy, and mesh
   certification patterns,
7. documentation, wiki publication, RFC closure, supported-features, and branch-hygiene controls,
8. live evidence bundle and canonical front-office proof routing for later product-surface slices.

RFC-0024 must reuse these controls. It must not add a `lotus-advise`-only memo certification
framework, local mesh substitute, or local wiki publication path. If a later memo slice discovers a
repeatable gap that would benefit other Lotus apps, that change belongs in `lotus-platform` with
platform-native tests and PR evidence.

## Reviewed Automation And Scaffolding

| Review area | Existing control | Slice 1 conclusion |
| --- | --- | --- |
| API certification and Swagger/OpenAPI quality | `make openapi-gate`, `scripts/openapi_quality_gate.py`, OpenAPI contract tests, route inventory tests, Feature Lane and PR Merge Gate jobs | Sufficient. Memo endpoints introduced later must include field descriptions, examples, error examples, idempotency/correlation documentation, stale-route absence checks, and route inventory coverage. |
| API vocabulary and no-alias governance | `make api-vocabulary-gate`, `make no-alias-gate`, generated API vocabulary inventory, platform vocabulary contracts | Sufficient. Memo fields must use private-banking vocabulary and must not introduce compatibility aliases unless a downstream consumer is proven. |
| Observability and bounded metrics | `/platform/capabilities`, existing supportability posture tests, bounded metric-label governance, production-profile smoke | Sufficient for pre-implementation. Memo metrics must use bounded labels such as audience, section readiness, source family, dependency family, and result posture rather than proposal ids, client ids, account ids, or narrative text. |
| Health, liveness, readiness, and dependency supportability | `/health`, `/health/live`, `/health/ready`, dependency readiness probes, runtime smoke, production guardrail negatives | Sufficient. Memo support must remain unavailable or degraded until required proposal, source, persistence, report, archive, AI, Gateway, and Workbench dependencies are implementation-backed. |
| Structured logging, correlation, and error handling | Existing correlation helpers, API error response tests, problem-details conventions, production guardrails | Sufficient. Memo slices must log support-safe identifiers and lineage refs, not client narrative, raw holdings, suitability detail, or personal data. |
| Test scaffolding | Repository unit/integration/e2e suites, Postgres parity tests, OpenAPI/vocabulary/no-alias gates, live runtime evidence helpers | Sufficient. Memo implementation must add lower-level domain tests before API tests, then integration and live proof only for behavior not already pinned lower in the test pyramid. |
| CI lane defaults | Feature Lane, PR Merge Gate, Main Releasability Gate, Docker build validation, Postgres migration smoke | Sufficient. Memo-bearing PRs must run repo-native local gates before PR and use GitHub lanes as merge truth. |
| Documentation and wiki scaffolding | Repo-local `wiki/`, `Sync-RepoWikis.ps1`, RFC index, supported-features page, documentation layering guidance, docs contract tests | Sufficient. Memo docs must remain implementation-backed and audience-aware; wiki source changes must publish after merge. |
| Governance hooks | Stranded-truth reconciliation, PR loop, branch hygiene, RFC evidence index, supported-feature non-claiming tests | Sufficient. Slice closure must remain on `main`; no memo truth may remain only on a side branch. |
| Security baseline | Dependency audit, production profile guardrails, sensitive-data handling expectations, no raw narrative/PII in logs or archive summaries | Sufficient for scaffolding. Later memo slices must add focused security and sensitive-data tests around memo projection, report packages, archive metadata, and AI prompts. |
| Domain-data-product onboarding | `contracts/domain-data-products/`, platform mesh contracts, `make domain-data-products-gate`, mesh certification tooling | Sufficient. `AdvisoryProposalMemoEvidencePack:v1` must not be declared until deterministic memo evidence, producer contract, trust telemetry, and supportability semantics exist. |
| Trust telemetry | `contracts/trust-telemetry/`, platform trust telemetry validator, RFC-0087 contract family | Sufficient. Memo telemetry must validate source freshness, section readiness, replayability, dependency posture, and support-safe evidence refs before capability promotion. |
| Live-evidence capture | `scripts/run_live_runtime_evidence_bundle.py`, repo live validation patterns, platform canonical front-office runtime route for Workbench proof | Sufficient. Later live proof must capture request/response artifacts under non-git-tracked `output/` and review every material memo field before supported-feature promotion. |

## Rejected One-Off Local Scaffolding

This slice deliberately rejects:

1. a `lotus-advise`-only memo certification CLI before the memo contract exists,
2. a local proof-pack schema that duplicates platform evidence and mesh controls,
3. a local OpenAPI or vocabulary validator outside the repo-native gate chain,
4. a local trust telemetry substitute before `AdvisoryProposalMemoEvidencePack:v1` exists,
5. local wiki publication scripts outside `Sync-RepoWikis.ps1`,
6. UI or report proof scaffolding before canonical Advise memo endpoints and report contracts exist.

These additions would increase maintenance cost without reducing RFC-0024 risk. The current risk is
source and supportability discipline: every memo section must be source-backed, explicitly
`PENDING_REVIEW`, explicitly `BLOCKED`, or explicitly `NOT_AVAILABLE`.

## Required Controls For Later RFC-0024 Slices

| Later slice need | Required control |
| --- | --- |
| Memo cleanup and structure | Dedicated memo domain, projection, persistence, report-handoff, AI-handoff, and supportability modules; no controller or UI-local business logic. |
| Memo domain model and builder | Unit tests for section readiness, source refs, audience projection, source freshness, hash determinism, blocked posture, and no positive claims for missing fee, conflict, policy, or client-ready evidence. |
| Memo persistence, replay, and idempotency | Postgres parity tests, immutable version/replay tests, idempotency conflict tests, correlation tests, audit history tests, and migration smoke. |
| Memo API contract | OpenAPI field descriptions and examples, problem-details examples, API vocabulary/no-alias gates, route inventory tests, and stale endpoint absence checks. |
| Memo data-product promotion | `AdvisoryProposalMemoEvidencePack:v1` producer declaration, trust telemetry snapshot, SLO/access/evidence policy, mesh certification, and conservative `/platform/capabilities` promotion. |
| Source-owner gaps | Owner-repo implementation where memo-critical facts are required; otherwise explicit `PENDING_REVIEW`, `BLOCKED`, or `NOT_AVAILABLE` posture in the memo section. |
| Report, render, and archive package | Typed memo package contract, report/render/archive tests, support-safe archive summaries, lineage refs, and no client-ready claim without review and retention evidence. |
| AI memo commentary | Deterministic memo evidence first; AI workflow pack may draft bounded text only from source-backed memo sections and must remain non-authoritative. |
| Gateway and Workbench realization | Gateway contract tests, Workbench API abstraction tests, meaningful UI tests, canonical front-office runtime proof, and no UI-local memo inference. |
| Documentation and commercial proof | README/wiki/supported-features updates only after implementation evidence; diagrams and demo material must separate implemented support from planned scope. |

## No Platform Change Rationale

The current gap is not missing platform automation. The current gap is disciplined memo product
definition inside `lotus-advise`:

1. creating a first-class memo evidence aggregate instead of repackaging proposal artifacts,
2. preserving source authority and readiness gaps without inventing upstream facts,
3. preventing premature data-product, Gateway, Workbench, report, archive, AI, and client-ready
   claims,
4. keeping the implementation modular before adding API and downstream scope.

Those risks are better controlled by RFC-0024 Slice 0 and Slice 1 source truth, focused docs
contract tests, repo-native gates, and later implementation tests than by adding a new platform
automation surface now.

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Stranded-truth reconciliation | `git fetch origin --prune` and `git branch -r --no-merged origin/main` returned no unmerged remote branches before Slice 1 implementation. |
| Platform automation review | Reviewed `lotus-platform` automation, mesh contracts, trust telemetry contracts, docs/wiki synchronization, RFC closure governance, canonical front-office routing, and validation guidance relevant to memo execution. |
| Repo-native gate review | Reviewed `lotus-advise` Makefile gates, OpenAPI/vocabulary/no-alias controls, docs contract tests, capabilities posture, live runtime evidence helpers, and existing RFC-0023 implementation evidence pattern. |
| No one-off scaffold decision | Recorded explicit rejection of local-only memo certification, mesh, OpenAPI, telemetry, wiki, UI, and report scaffolds before the memo contract exists. |
| Next-slice readiness | RFC-0024 may proceed to Slice 2 cleanup and structure using existing platform and repo-native gates. |

## Wiki And README Decision

Wiki source is updated because RFC implementation status and product-roadmap truth changed. README
does not change in this slice because command surfaces, runtime behavior, and supported feature
entrypoints did not change.
