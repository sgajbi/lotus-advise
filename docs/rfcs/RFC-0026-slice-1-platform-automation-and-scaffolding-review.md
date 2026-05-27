# RFC-0026 Slice 1: Platform Automation and Scaffolding Review

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0026: Advisor Cockpit Operating Workflow |
| **Slice** | 1 - platform automation and scaffolding improvement |
| **Status** | IMPLEMENTED - REVIEWED; NO PLATFORM CHANGE REQUIRED BEFORE COCKPIT DOMAIN WORK |
| **Implemented Date** | 2026-05-27 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0026-advisor-cockpit-gold-standard` |
| **Capability Posture** | This slice does not implement advisor cockpit APIs, action-item persistence, acknowledgement writes, data-product promotion, Gateway routes, Workbench cockpit surfaces, canonical RFC-0026 seed data, or client-demo claims. Those remain mandatory RFC-0026 work in subsequent slices. This slice proves RFC-0026 can proceed using existing platform controls and defines the cockpit-specific controls subsequent implementation slices must satisfy. |

## Decision

No `lotus-platform` code or automation change is required before RFC-0026 proceeds to cleanup,
cockpit domain modeling, source-read-model aggregation, priority/SLA semantics, APIs,
acknowledgements, Gateway, Workbench, data-product promotion, canonical automation, and proof
slices.

The review found that current Lotus platform and repo-native automation already provide the
reusable governance controls needed for the first advisor cockpit implementation wave:

1. API certification and Swagger/OpenAPI quality gates,
2. API vocabulary and no-alias governance,
3. cursor-pagination vocabulary and existing paginated API examples,
4. health, readiness, dependency supportability, bounded metrics, and production guardrails,
5. structured logging, correlation, problem-details, and safe error handling,
6. unit, integration, e2e, migration, Docker, coverage, and GitHub CI lane posture,
7. domain-data-product onboarding, trust telemetry, SLO, access, evidence policy, and mesh
   certification patterns,
8. documentation layering, wiki publication, RFC closure, supported-features, and branch-hygiene
   controls,
9. canonical front-office runtime proof routing for subsequent Gateway/Workbench cockpit surfaces,
10. heartbeat and async-monitoring guidance for long-running live validation and CI.

RFC-0026 must reuse these controls. It must not add a `lotus-advise`-only cockpit certification
framework, a local mesh substitute, a platform-wide generic action-item framework before a second
producer needs it, or a cockpit-specific canonical seed contract before the backend, Gateway, and
Workbench behavior exists. If a subsequent cockpit slice discovers a repeatable gap that would
benefit other Lotus apps, that change belongs in `lotus-platform` with platform-native tests and PR
evidence inside the RFC-0026 implementation program.

## Reviewed Automation and Scaffolding

| Review area | Existing control | Slice 1 conclusion |
| --- | --- | --- |
| API certification and Swagger/OpenAPI quality | `make openapi-gate`, `scripts/openapi_quality_gate.py`, OpenAPI contract tests, route inventory tests, Feature Lane, PR Merge Gate, and Main Releasability Gate jobs | Sufficient. Cockpit endpoints introduced in subsequent slices must include field descriptions, examples, error examples, idempotency/correlation documentation, stale-route absence checks, and route inventory coverage. |
| API vocabulary and no-alias governance | `make api-vocabulary-gate`, `make no-alias-gate`, generated API vocabulary inventory, and platform vocabulary contracts | Sufficient. Cockpit fields must use private-banking workflow vocabulary and must not introduce compatibility aliases unless a downstream dependency is proven and migrated. |
| Cursor pagination | Existing `cursor` and `next_cursor` vocabulary, platform API vocabulary contracts, and repo-native paginated endpoint patterns | Sufficient for implementation start. RFC-0026 must still add cockpit-specific tests for default page size, maximum page size, invalid cursor, next cursor, stable ordering, and entitlement-projected pages. |
| Read-model and action-item structure | Existing proposal lifecycle/read-model modularity in `lotus-advise`, plus platform service-scaffold guidance for thin controllers and domain modules | Sufficient. A platform-wide generic action-item framework is rejected until more than one producer proves the same abstraction. Cockpit read models should be first-class `lotus-advise` modules. |
| Observability and bounded metrics | `/platform/capabilities`, dependency readiness probes, supportability tests, bounded metric-label governance, production-profile guardrails | Sufficient. Cockpit metrics must use bounded labels such as action family, priority, status, owner role, source family, dependency family, and SLA aging band; they must not include client, portfolio, proposal, action item, policy, memo, report, execution, trace, or correlation identifiers. |
| Health, liveness, readiness, and dependency supportability | `/health`, `/health/live`, `/health/ready`, runtime smoke, dependency probes, production guardrail negatives | Sufficient. Cockpit support must remain unavailable or degraded until required source, policy, memo, report, archive, AI, Gateway, and Workbench dependencies are implementation-backed. |
| Structured logging, correlation, and error handling | Existing correlation helpers, problem-details conventions, API error response tests, sensitive-data guardrails | Sufficient. Cockpit logs must use support-safe identifiers and reason families, not raw client profile, holdings, memo, policy, AI, report, archive, execution, or storage payloads. |
| Test scaffolding | Repository unit/integration/e2e suites, Postgres parity tests, OpenAPI/vocabulary/no-alias gates, live runtime evidence helpers | Sufficient. Cockpit implementation must add pure domain tests first, then API and persistence tests, then Gateway/Workbench/browser/live proof where lower layers cannot prove behavior. |
| CI lane defaults | Feature Lane, PR Merge Gate, Main Releasability Gate, Docker build validation, coverage gate, Postgres migration smoke | Sufficient. Cockpit-bearing PRs must run repo-native local gates before PR and treat GitHub PR/Main gates as merge and closure truth. |
| Documentation and wiki scaffolding | Repo-local `wiki/`, `Sync-RepoWikis.ps1`, RFC index, supported-features page, documentation layering guidance, docs contract tests | Sufficient. Cockpit wiki and commercial material must be implementation-backed, multi-audience, and non-duplicative; wiki source must publish after merge when changed. |
| Governance hooks | Stranded-truth reconciliation, PR loop, branch hygiene, RFC evidence index, supported-feature non-claiming tests | Sufficient. Cockpit closure truth must land on `main`; no source map, data-product, wiki, canonical seed, or proof truth may remain only on a side branch. |
| Security baseline | Dependency audit, production profile guardrails, sensitive-data expectations, metric-label restrictions, audit-event expectations | Sufficient for scaffolding. Later slices must add focused tests around entitlement projection, acknowledgement writes, supportability projection, evidence access classes, and sensitive payload handling. |
| Domain-data-product onboarding | `contracts/domain-data-products/`, platform mesh contracts, `make domain-data-products-gate`, mesh certification tooling | Sufficient. `AdvisorCockpitOperatingSnapshot:v1` and `AdvisoryActionItemRegister:v1` must not be promoted until runtime evidence, producer declarations, trust telemetry, SLO/access/evidence posture, capabilities, and catalog certification are real. |
| Trust telemetry | `contracts/trust-telemetry/`, platform trust telemetry validator, RFC-0087 contract family | Sufficient. Cockpit telemetry must validate source freshness, action completeness, policy/memo/report lineage, dependency readiness, and support-safe evidence refs before capability promotion. |
| Canonical front-office automation | Governed `lotus-workbench` runtime, canonical `PB_SG_GLOBAL_BAL_001` proof path, platform canonical data contracts, and live validation module pattern | Sufficient for implementation start. RFC-0026 must add `RFC26_ADVISOR_COCKPIT_CANONICAL` seed/contracts and `scripts/live/validation/advisor-cockpit-proof.mjs` only after backend, Gateway, and Workbench cockpit behavior exists. |
| Live-evidence capture | Repo live validation patterns, platform canonical front-office routing, non-git-tracked `output/` evidence convention, heartbeat guidance for long-running automation | Sufficient. Later live proof must capture request/response artifacts under `output/` and critically review every material status, count, priority, reason code, owner role, source gap, lineage ref, and degraded state. |

## Rejected One-Off Scaffolding

This slice deliberately rejects:

1. a `lotus-advise`-only cockpit certification CLI before cockpit endpoints exist,
2. a local cockpit proof-pack schema that duplicates platform evidence and mesh controls,
3. a platform-wide generic action-item framework before a reusable multi-app pattern is proven,
4. a cockpit-specific platform canonical data contract before backend/Gateway/Workbench behavior
   exists,
5. a Workbench live proof module before Gateway-backed cockpit APIs exist,
6. a local OpenAPI or vocabulary validator outside the repo-native gate chain,
7. a local trust telemetry substitute before cockpit data products exist,
8. local wiki publication scripts outside `Sync-RepoWikis.ps1`,
9. UI, report, archive, execution, or AI proof scaffolding before canonical Advise cockpit
   endpoints and typed downstream contracts exist.

These additions would increase maintenance cost without reducing RFC-0026 risk. The current risk is
source authority and workflow discipline: every cockpit action must be source-backed, explicitly
`READY`, explicitly `PENDING_REVIEW`, explicitly `BLOCKED`, explicitly degraded, or explicitly
unsupported without UI-local inference or unsupported client-ready wording.

## Required Controls for Later RFC-0026 Slices

| Subsequent RFC-0026 slice need | Required control |
| --- | --- |
| Cleanup and structure | Dedicated cockpit domain, source-read-model, priority, SLA, acknowledgement, API, supportability, and evidence modules; no controller or UI-local business logic. |
| Cockpit domain model and vocabulary | Unit tests for action families, statuses, priority values, owner roles, reason codes, source readiness, evidence refs, lineage refs, and private-banking terminology. |
| Source read models and performance | Repository-native list/read methods, no N+1 reads, degraded-source tests, realistic advisor-book benchmark, and deterministic pagination tests. |
| Priority, next action, and SLA aging | Pure unit tests for all first-wave action families, tie-breakers, blocked posture, acknowledgement boundaries, and unsupported capability posture. |
| Snapshot and action APIs | OpenAPI field descriptions and examples, problem-details examples, API vocabulary/no-alias gates, route inventory tests, idempotency/correlation tests, and stale endpoint absence checks. |
| Meeting preparation and follow-up | Source-backed preparation packet tests, owner-boundary tests, acknowledgement audit/replay tests, and no CRM/calendar ownership overclaim. |
| Supervisory queues | Entitlement-projected queue tests, SLA aging tests, advisor/supervisor view tests, and no UI-local review-state inference. |
| Report, archive, execution, and house-view readiness | Downstream owner-boundary payloads, typed downstream contract tests where needed, and no cockpit claim dependent on an unimplemented downstream surface. |
| Data-product promotion | `AdvisorCockpitOperatingSnapshot:v1` and `AdvisoryActionItemRegister:v1` producer declarations, trust telemetry, SLO/access/evidence policy, mesh certification, and conservative `/platform/capabilities` promotion. |
| Gateway and Workbench realization | Gateway contract tests, Workbench API abstraction tests, browser tests, canonical front-office runtime proof, and no UI-local priority or workflow inference. |
| Canonical automation | Platform canonical contract/invariant updates, Workbench `advisor-cockpit-proof.mjs`, `npm run live:stack:up:validate` proof, and lowest-useful-layer regression tests for every live defect. |
| Documentation and commercial proof | README/wiki/supported-features updates only after implementation evidence; diagrams and demo material must separate cockpit support from RFC-0028 full demo/RFP claims. |

## No Platform Change Rationale

The current gap is not missing platform automation. The current gap is disciplined cockpit product
definition inside `lotus-advise` and strict Gateway/Workbench realization in subsequent RFC-0026
slices:

1. creating first-class cockpit models instead of stretching proposal lifecycle responses,
2. preserving source authority and source-readiness gaps without inventing missing client,
   household, meeting, policy, memo, report, execution, or DPM facts,
3. preventing premature cockpit data-product, Gateway, Workbench, demo, CRM, OMS, AI, and
   client-ready claims,
4. keeping priority, SLA, and acknowledgement semantics backend-owned,
5. using platform-owned validation, mesh, wiki, runtime, and CI controls instead of adding
   cockpit-only scaffolding.

Those risks are better controlled by RFC-0026 Slice 0 and Slice 1 source truth, focused docs
contract tests, repo-native gates, and subsequent implementation tests than by adding a new
platform automation surface now.

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Stranded-truth reconciliation | `git fetch origin --prune` and `git branch -r --no-merged origin/main` returned no unmerged remote branches before RFC-0026 implementation began. |
| Platform automation review | Reviewed `lotus-platform` service scaffolding, OpenAPI conformance, domain-data-product onboarding, trust telemetry, mesh certification, docs/wiki synchronization, canonical front-office runtime routing, and heartbeat/async guidance relevant to cockpit execution. |
| Repo-native gate review | Reviewed `lotus-advise` Makefile gates, OpenAPI/vocabulary/no-alias controls, docs contract tests, capabilities posture, live runtime evidence helpers, data-product/trust telemetry contracts, and RFC-0023/RFC-0024/RFC-0025 evidence patterns. |
| No one-off scaffold decision | Recorded explicit rejection of local-only cockpit certification, mesh, action-item framework, canonical seed, OpenAPI, telemetry, wiki, UI, report, archive, execution, and AI scaffolds before the cockpit contract exists. |
| Next-slice readiness | RFC-0026 may proceed to Slice 2 cleanup and structure using existing platform and repo-native gates. |

## Wiki and README Decision

Wiki source and the RFC index are updated because RFC-0026 implementation status and product-roadmap
truth changed. README does not change in this slice because command surfaces, runtime behavior, and
supported feature entrypoints did not change.
