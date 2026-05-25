# RFC-0025 Slice 1: Platform Automation and Scaffolding Review

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0025: Enterprise Suitability and Best-Interest Policy Packs |
| **Slice** | 1 - platform automation and scaffolding improvement |
| **Status** | IMPLEMENTED - REVIEWED; NO PLATFORM CHANGE REQUIRED BEFORE POLICY DOMAIN WORK |
| **Implemented Date** | 2026-05-26 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc25-slice1-platform-scaffolding-review` |
| **Capability Posture** | This slice does not implement policy-pack catalog APIs, policy activation, policy evaluation, policy persistence, review queues, report/render/archive sign-off packs, Gateway/Workbench policy surfaces, data-product promotion, or client-ready publication. It proves RFC-0025 can proceed using existing platform controls and defines the policy-specific controls later implementation slices must satisfy. |

## Decision

No `lotus-platform` code or automation change is required before RFC-0025 proceeds to cleanup,
policy-domain modeling, source-owner integration, API, data-product, report, Gateway, Workbench,
and proof slices.

The review found that existing Lotus platform and repo-native automation already provide the
reusable governance controls needed for the first enterprise policy-pack implementation wave:

1. API certification and Swagger/OpenAPI quality gates,
2. API vocabulary and no-alias governance,
3. health, readiness, capabilities, dependency supportability, and bounded metric-label posture,
4. structured logging, correlation, problem-details, and production-profile guardrail
   expectations,
5. unit, integration, e2e, migration, Docker, coverage, and main releasability CI lanes,
6. domain-data-product onboarding, trust telemetry, SLO, access, evidence policy, and mesh
   certification patterns,
7. documentation layering, wiki publication, RFC closure, supported-features, and branch-hygiene
   controls,
8. canonical front-office runtime proof routing for later Gateway/Workbench policy surfaces,
9. agent heartbeat and async-monitoring guidance for long-running cross-repo checks.

RFC-0025 must reuse these controls. It must not add a `lotus-advise`-only policy certification
framework, local mesh substitute, local policy-pack schema registry, or local wiki publication
path. If a later policy slice discovers a repeatable gap that would benefit other Lotus apps, that
change belongs in `lotus-platform` with platform-native tests and PR evidence.

## Reviewed Automation and Scaffolding

| Review area | Existing control | Slice 1 conclusion |
| --- | --- | --- |
| API certification and Swagger/OpenAPI quality | `make openapi-gate`, `scripts/openapi_quality_gate.py`, OpenAPI contract tests, route inventory tests, Feature Lane, PR Merge Gate, and Main Releasability Gate jobs | Sufficient. Policy endpoints introduced later must include field descriptions, examples, error examples, idempotency/correlation documentation, replay semantics, stale-route absence checks, and route inventory coverage. |
| API vocabulary and no-alias governance | `make api-vocabulary-gate`, `make no-alias-gate`, generated API vocabulary inventory, platform vocabulary contracts | Sufficient. Policy-pack fields must use private-banking vocabulary and must not introduce compatibility aliases unless a downstream dependency is proven and migrated. |
| Policy-pack schema validation | Existing JSON/Pydantic validation patterns, repo-native unit tests, platform contract schema patterns, and `lotus-platform` onboarding bundle examples | Sufficient for first-wave implementation. Policy-pack schemas should live in `lotus-advise` until a cross-app policy-pack registry exists; only reusable schema-validation patterns should move to `lotus-platform`. |
| Policy sample fixtures | Existing unit/golden fixture patterns and canonical `PB_SG_GLOBAL_BAL_001` front-office proof path | Sufficient. Reference packs must be clearly labeled as examples and must not be described as legal advice or production-approved bank regulatory content. |
| Observability and bounded metrics | `/platform/capabilities`, dependency readiness probes, supportability tests, bounded metric-label governance, production-profile guardrails | Sufficient. Policy metrics must use bounded labels such as policy family, rule family, status, severity, source family, review route, and dependency family; they must not include client, account, portfolio, proposal, policy-pack, rule, or evaluation identifiers. |
| Health, liveness, readiness, and dependency supportability | `/health`, `/health/live`, `/health/ready`, runtime smoke, dependency probes, production guardrail negatives | Sufficient. Policy support must remain unavailable or degraded until required source, persistence, report, archive, AI, Gateway, and Workbench dependencies are implementation-backed. |
| Structured logging, correlation, and error handling | Existing correlation helpers, problem-details conventions, API error response tests, sensitive-data guardrails | Sufficient. Policy logs must use support-safe identifiers and reason families, not raw client profile, holdings, product details, proprietary policy content, prompt text, or model output. |
| Test scaffolding | Repository unit/integration/e2e suites, Postgres parity tests, OpenAPI/vocabulary/no-alias gates, live runtime evidence helpers | Sufficient. Policy implementation must add pure domain tests before API tests, then persistence/integration/live proof only where lower-level tests cannot prove the behavior. |
| CI lane defaults | Feature Lane, PR Merge Gate, Main Releasability Gate, Docker build validation, coverage gate, Postgres migration smoke | Sufficient. Policy-bearing PRs must run repo-native local gates before PR and treat GitHub PR/Main gates as merge and closure truth. |
| Documentation and wiki scaffolding | Repo-local `wiki/`, `Sync-RepoWikis.ps1`, RFC index, supported-features page, documentation layering guidance, docs contract tests | Sufficient. Policy-pack wiki and commercial material must be implementation-backed, multi-audience, and non-duplicative; wiki source must publish after merge when changed. |
| Governance hooks | Stranded-truth reconciliation, PR loop, branch hygiene, RFC evidence index, supported-feature non-claiming tests | Sufficient. Policy-pack closure truth must land on `main`; no source map, data-product, wiki, or proof truth may remain only on a side branch. |
| Security baseline | Dependency audit, production profile guardrails, sensitive-data expectations, metric-label restrictions, audit-event expectations | Sufficient for scaffolding. Later slices must add focused tests around policy content, review actions, waiver/override posture, sign-off packages, archive summaries, and AI evidence packets. |
| Domain-data-product onboarding | `contracts/domain-data-products/`, platform mesh contracts, `make domain-data-products-gate`, mesh certification tooling | Sufficient. `AdvisoryPolicyEvaluationRecord:v1` must not be promoted until evaluation evidence, producer declaration, trust telemetry, SLO/access/evidence posture, capabilities, and catalog certification are real. |
| Trust telemetry | `contracts/trust-telemetry/`, platform trust telemetry validator, RFC-0087 contract family | Sufficient. Policy telemetry must validate source freshness, rule coverage, review posture, replayability, dependency readiness, and support-safe evidence refs before capability promotion. |
| Live-evidence capture | `scripts/run_live_runtime_evidence_bundle.py`, repo live validation patterns, governed Workbench runtime and `PB_SG_GLOBAL_BAL_001` proof route | Sufficient. Later live proof must capture request/response artifacts under non-git-tracked `output/` and critically review every material policy result, reason code, source ref, hash, lineage ref, approval dependency, disclosure, consent, SLA state, and degraded state. |

## Rejected One-Off Local Scaffolding

This slice deliberately rejects:

1. a `lotus-advise`-only policy certification CLI before the policy contract exists,
2. a local policy proof-pack schema that duplicates platform evidence and mesh controls,
3. a local policy-pack registry in `lotus-platform` before more than one app has a real reusable
   need,
4. a local OpenAPI or vocabulary validator outside the repo-native gate chain,
5. a local trust telemetry substitute before `AdvisoryPolicyEvaluationRecord:v1` exists,
6. local wiki publication scripts outside `Sync-RepoWikis.ps1`,
7. Gateway, Workbench, report, archive, or AI proof scaffolding before canonical Advise policy
   endpoints and typed downstream contracts exist.

These additions would increase maintenance cost without reducing RFC-0025 risk. The current risk is
source and supportability discipline: every policy outcome must be source-backed, explicitly
`PENDING_REVIEW`, explicitly `BLOCKED`, or explicitly unavailable without positive best-interest,
eligibility, disclosure, consent, or client-ready wording.

## Required Controls for Later RFC-0025 Slices

| Later slice need | Required control |
| --- | --- |
| Cleanup and structure | Dedicated policy domain, configuration, validation, evaluation, persistence, replay, API, review-queue, sign-off-package, AI-handoff, report-handoff, and supportability modules; no controller or UI-local business logic. |
| Policy-pack catalog and activation | Schema validation tests, immutable activation events, maker-checker tests where configured, sample dry-run validation, content hashes, and audit events. |
| Applicability and rule evaluation | Pure unit tests for jurisdiction, booking center, legal entity, client segment, mandate, product, complex-product, conflict, disclosure, consent, missing-source, degraded-source, and best-interest paths. |
| Source-owner gaps | Owner-repo implementation where policy-critical facts are required; otherwise explicit `PENDING_REVIEW`, `BLOCKED`, or unavailable posture in the policy evaluation. |
| Persistence, replay, and idempotency | Postgres parity tests, immutable evaluation/replay tests, idempotency conflict tests, correlation tests, audit history tests, and migration smoke. |
| Certified policy APIs | OpenAPI field descriptions and examples, problem-details examples, API vocabulary/no-alias gates, route inventory tests, and stale endpoint absence checks. |
| Policy data-product promotion | `AdvisoryPolicyEvaluationRecord:v1` producer declaration, trust telemetry snapshot, SLO/access/evidence policy, mesh certification, and conservative `/platform/capabilities` promotion. |
| Report, render, and archive package | Typed policy package contract, report/render/archive tests, support-safe archive summaries, lineage refs, retention/access-audit posture, and no client-ready claim without review, consent, disclosure, and retention evidence. |
| AI policy-evidence consumption | Deterministic policy evidence first; AI workflow packs may summarize bounded policy evidence only and must remain non-authoritative. |
| Gateway and Workbench realization | Gateway contract tests, Workbench API abstraction tests, meaningful UI tests, canonical front-office runtime proof, and no UI-local policy inference. |
| Documentation and commercial proof | README/wiki/supported-features updates only after implementation evidence; diagrams and demo material must separate implemented support from planned scope and legal-advice non-claims. |

## No Platform Change Rationale

The current gap is not missing platform automation. The current gap is disciplined policy-product
definition inside `lotus-advise` and source-owner integration across the ecosystem:

1. creating a first-class `AdvisoryPolicyEvaluationRecord` instead of stretching the existing
   suitability scanner,
2. preserving source authority and readiness gaps without inventing upstream product, risk, fee,
   conflict, or client facts,
3. preventing premature policy data-product, Gateway, Workbench, report, archive, AI, legal,
   regulatory, and client-ready claims,
4. keeping policy modules clean before adding API and downstream scope,
5. using platform-owned validation, mesh, wiki, runtime, and CI controls instead of adding
   policy-pack-only scaffolding.

Those risks are better controlled by RFC-0025 Slice 0 and Slice 1 source truth, focused docs
contract tests, repo-native gates, and later implementation tests than by adding a new platform
automation surface now.

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Stranded-truth reconciliation | `git fetch origin --prune` and `git branch -r --no-merged origin/main` returned no unmerged remote branches before Slice 1 implementation. |
| Platform automation review | Reviewed `lotus-platform` documentation layering, wiki synchronization, domain-product onboarding, trust telemetry, mesh SLO/access/evidence policy, canonical front-office proof routing, heartbeat/async monitoring guidance, and service scaffolding standards relevant to policy execution. |
| Repo-native gate review | Reviewed `lotus-advise` Makefile gates, OpenAPI/vocabulary/no-alias controls, docs contract tests, capabilities posture, live runtime evidence helpers, data-product/trust telemetry contracts, and existing RFC-0023/RFC-0024 implementation evidence patterns. |
| No one-off scaffold decision | Recorded explicit rejection of local-only policy certification, mesh, schema-registry, OpenAPI, telemetry, wiki, UI, report, archive, and AI scaffolds before the policy contract exists. |
| Next-slice readiness | RFC-0025 may proceed to Slice 2 cleanup and structure using existing platform and repo-native gates. |

## Wiki and README Decision

Wiki source is updated because RFC implementation status and product-roadmap truth changed. README
does not change in this slice because command surfaces, runtime behavior, and supported feature
entrypoints did not change.
