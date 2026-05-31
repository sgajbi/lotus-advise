# RFC-0027 Slice 1: Platform Automation and Scaffolding Review

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0027: Governed Advisory AI Copilot |
| **Slice** | 1 - platform automation and scaffolding improvement |
| **Status** | IMPLEMENTED - REVIEWED; NO PLATFORM CHANGE REQUIRED BEFORE COPILOT DOMAIN WORK |
| **Implemented Date** | 2026-05-28 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0027-governed-advisory-ai-copilot` |
| **Capability Posture** | This slice does not implement copilot APIs, evidence-packet persistence, guardrail execution, `lotus-ai` workflow-pack integration, review actions, data-product promotion, Gateway routes, Workbench copilot surfaces, canonical RFC-0027 seed data, or client/demo claims. Those remain mandatory RFC-0027 work in subsequent slices. This slice proves RFC-0027 can proceed using existing platform controls and defines the copilot-specific controls later implementation slices must satisfy. |

## Decision

No `lotus-platform` code or automation change is required before RFC-0027 proceeds to cleanup,
copilot domain modeling, evidence-packet construction, guardrails, `lotus-ai` workflow-pack
integration, run persistence, certified APIs, Gateway, Workbench, canonical automation,
data-product promotion, and proof slices.

Copilot APIs, evidence packets, guardrails, `lotus-ai` execution, Gateway/Workbench product
surfaces, canonical RFC-0027 seed data, live proof, data-product promotion, and supported claims
remain mandatory subsequent RFC-0027 work and are unpromoted in this slice.

The review found that current Lotus platform and repo-native automation already provide the
reusable governance controls needed for the first governed advisory copilot implementation wave:

1. API certification and Swagger/OpenAPI quality gates,
2. API vocabulary and no-alias governance,
3. health, readiness, dependency supportability, bounded metrics, and production guardrails,
4. structured logging, correlation, problem-details, and safe error handling,
5. unit, integration, e2e, migration, Docker, coverage, and GitHub CI lane posture,
6. workflow security and GitHub action runtime validation,
7. domain-data-product onboarding, trust telemetry, SLO, access, evidence policy, and mesh
   certification patterns,
8. documentation layering, wiki publication, RFC closure, supported-features, and branch-hygiene
   controls,
9. canonical front-office runtime proof routing for subsequent Gateway/Workbench copilot surfaces,
10. heartbeat and async-monitoring guidance for long-running live validation and CI.

RFC-0027 must reuse these controls. It must not add a `lotus-advise`-only copilot certification
framework, a local mesh substitute, a local prompt registry, a parallel workflow-pack registry, a
local wiki publication path, or a platform-wide generic copilot framework before more than one
producer proves the same abstraction. If a subsequent copilot slice discovers a repeatable gap that
would benefit other Lotus apps, that change belongs in `lotus-platform` with platform-native tests
and PR evidence inside the RFC-0027 implementation program.

## Reviewed Automation and Scaffolding

| Review area | Existing control | Slice 1 conclusion |
| --- | --- | --- |
| API certification and Swagger/OpenAPI quality | `make openapi-gate`, OpenAPI contract tests, route inventory tests, Feature Lane, PR Merge Gate, and Main Releasability Gate jobs | Sufficient. Copilot endpoints introduced later must include field descriptions, examples, error examples, idempotency/correlation documentation, stale-route absence checks, route inventory coverage, and safe degraded/unsupported/guardrail examples. |
| API vocabulary and no-alias governance | `make api-vocabulary-gate`, `make no-alias-gate`, generated API vocabulary inventory, and platform vocabulary contracts | Sufficient. Copilot fields must use private-banking advisory, evidence, review, supportability, and lineage vocabulary. Compatibility aliases are not allowed unless a downstream dependency is proven and migrated. |
| Workflow security and CI action posture | `automation/validate_workflow_security.py` and `automation/validate_workflow_action_runtime.py` validate platform workflow permissions and action runtime baselines | Sufficient. Copilot PRs must not introduce broad write permissions, unsafe `pull_request_target`, or stale action runtimes in reusable platform workflows. |
| Evidence-packet schema posture | Existing Pydantic/contract-test patterns, platform contract schemas, RFC-0023/RFC-0024/RFC-0025 evidence records, and repo-native documentation contract tests | Sufficient for implementation start. Evidence-packet schemas should live in `lotus-advise` until a second producer proves a reusable cross-app evidence-packet schema is needed. |
| `lotus-ai` workflow-pack boundary | Existing bounded workflow-pack adapter patterns in RFC-0023/RFC-0024/RFC-0025, plus platform workflow and security validators | Sufficient. RFC-0027 must still implement copilot-specific adapter tests proving `lotus-advise` sends only redacted evidence packets and approved workflow-pack instructions, never direct provider calls or UI-built prompts. |
| Guardrail and unsupported-evidence posture | Existing problem-details, reason-code, supportability, and documentation-contract patterns | Sufficient for implementation start. Guardrail reason codes, forbidden-action rejection, prompt-injection handling, unsupported-evidence responses, and unsafe wording rejection must be implemented in Advise with deterministic tests. |
| Observability and bounded metrics | `/platform/capabilities`, dependency readiness probes, supportability tests, bounded metric-label governance, and production-profile guardrails | Sufficient. Copilot metrics must use bounded labels such as action family, run status, review posture, guardrail reason family, dependency family, and AI availability posture. They must not include client, portfolio, proposal, evidence-packet, prompt, provider-run, trace, correlation, or raw source identifiers. |
| Health, liveness, readiness, and dependency supportability | `/health`, `/health/live`, `/health/ready`, runtime smoke, dependency probes, and production guardrail negatives | Sufficient. Copilot support must remain unavailable or degraded until required advisory evidence, `lotus-ai`, persistence, Gateway, Workbench, data-product, and proof dependencies are implementation-backed. |
| Structured logging, correlation, and error handling | Existing correlation helpers, problem-details conventions, API error response tests, sensitive-data guardrails, and safe logging conventions | Sufficient. Copilot logs must use support-safe identifiers and reason families, not raw prompts, raw provider responses, unrestricted source payloads, client profile details, holdings, policy content, memo text, or generated unsafe output. |
| Test scaffolding | Repository unit/integration/e2e suites, Postgres parity tests, OpenAPI/vocabulary/no-alias gates, live runtime evidence helpers | Sufficient. Copilot implementation must add pure domain tests first, then API/persistence/adapter tests, then Gateway/Workbench/browser/live proof where lower layers cannot prove behavior. |
| CI lane defaults | Feature Lane, PR Merge Gate, Main Releasability Gate, Docker build validation, coverage gate, dependency gates, and Postgres migration smoke | Sufficient. Copilot-bearing PRs must run repo-native local gates before PR and treat GitHub PR/Main gates as merge and closure truth. |
| Documentation and wiki scaffolding | Repo-local `wiki/`, `Sync-RepoWikis.ps1`, `-AllowUnpublishedSourceChanges`, RFC index, supported-features page, documentation layering guidance, and docs contract tests | Sufficient. Copilot wiki, README, API, operations, model-risk, and commercial material must be implementation-backed, multi-audience, and non-duplicative; wiki source must publish after merge when changed. |
| Governance hooks | Stranded-truth reconciliation, PR loop, branch hygiene, RFC evidence index, supported-feature non-claiming tests, and no-WTBD execution rules | Sufficient. Copilot closure truth must land on `main`; no source map, data-product, wiki, canonical seed, model-risk, or proof truth may remain only on a side branch. |
| Security baseline | Dependency audit, production profile guardrails, sensitive-data expectations, metric-label restrictions, audit-event expectations, and workflow-security validation | Sufficient for scaffolding. Later slices must add focused tests around entitlement projection, redaction, prompt injection, forbidden actions, review actions, retention, supportability projection, and sensitive payload handling. |
| Domain-data-product onboarding | `contracts/domain-data-products/`, platform mesh contracts, `make domain-data-products-gate`, mesh certification tooling, and trust telemetry validators | Sufficient. `AdvisoryCopilotInteractionRecord:v1` must not be promoted until runtime evidence, producer declarations, trust telemetry, SLO/access/evidence posture, capabilities, and catalog certification are real. |
| Trust telemetry | `contracts/trust-telemetry/`, platform trust telemetry validator, RFC-0087 contract family | Sufficient. Copilot telemetry must validate source freshness, evidence-packet completeness, guardrail posture, review posture, dependency readiness, and support-safe lineage refs before capability promotion. |
| Canonical front-office automation | Governed `lotus-workbench` runtime, canonical `PB_SG_GLOBAL_BAL_001` proof path, platform canonical data contracts, and live validation module pattern | Sufficient for implementation start. RFC-0027 must add `RFC27_ADVISORY_COPILOT_CANONICAL` seed/contracts and Workbench live validation only after backend, Gateway, and Workbench copilot behavior exists. That is RFC-0027 Slice 12 work, not deferred follow-up bucket. |
| Live-evidence capture | Repo live validation patterns, platform canonical front-office routing, non-git-tracked `output/` evidence convention, heartbeat guidance for long-running automation | Sufficient. Later live proof must capture request/response artifacts under `output/` and critically review every material statement, reason code, source ref, lineage ref, review posture, degraded posture, metric label, and guardrail outcome. |

## Rejected One-Off Scaffolding

This slice deliberately rejects:

1. a `lotus-advise`-only copilot certification CLI before copilot endpoints exist,
2. a local copilot proof-pack schema that duplicates platform evidence and mesh controls,
3. a local prompt or workflow-pack registry outside `lotus-ai`,
4. a platform-wide generic copilot framework before a reusable multi-app pattern is proven,
5. a copilot-specific platform canonical data contract before backend/Gateway/Workbench behavior
   exists,
6. a Workbench live proof module before Gateway-backed copilot APIs exist,
7. a local OpenAPI or vocabulary validator outside the repo-native gate chain,
8. a local trust telemetry substitute before copilot data-product promotion exists,
9. local wiki publication scripts outside `Sync-RepoWikis.ps1`,
10. UI, report, archive, operations, or model-risk proof scaffolding before canonical Advise
    copilot endpoints and typed downstream contracts exist.

These additions would increase maintenance cost without reducing RFC-0027 risk. The current risk is
source authority and AI governance discipline: every copilot answer must be source-backed,
explicitly `REVIEW_REQUIRED`, explicitly unsupported, explicitly guardrail-rejected, explicitly
degraded, or explicitly unavailable without UI-local inference, provider leakage, raw prompt
exposure, or unsupported client-ready wording.

## Required Controls for Later RFC-0027 Slices

| Subsequent RFC-0027 slice need | Required control |
| --- | --- |
| Cleanup and structure | Dedicated copilot catalog, evidence-packet, guardrail, workflow-pack adapter, run persistence, review, projection, supportability, and API modules; no controller, infrastructure, or UI-local business logic. |
| Copilot domain model and vocabulary | Unit tests for action families, audiences, statuses, review postures, unsupported postures, guardrail reason codes, source refs, lineage refs, retention classes, and private-banking terminology. |
| Evidence packets and redaction | Deterministic packet builders, role-aware projection, source hash tests, restricted-field exclusion tests, missing-evidence tests, and replay/rebuild posture without raw prompt reconstruction. |
| Guardrails and unsupported evidence | Hostile prompt tests, forbidden-action tests, unsupported-question tests, unsafe client-ready wording tests, reason-code stability tests, and blocked/degraded-state preservation. |
| `lotus-ai` workflow-pack integration | Adapter tests proving approved workflow-pack usage, no direct provider calls from `lotus-advise`, deterministic unavailable/disabled behavior, timeout posture, lineage capture, and model-risk evidence. |
| Run persistence, review, audit, and retention | Idempotent run/review tests, append-only audit events, retention/access posture, correlation tests, raw prompt/output non-exposure tests, and legal-hold documentation where applicable. |
| Certified Advise APIs | OpenAPI field descriptions and examples, problem-details examples, API vocabulary/no-alias gates, route inventory tests, idempotency/correlation tests, and stale endpoint absence checks. |
| Data-product promotion | `AdvisoryCopilotInteractionRecord:v1` producer declaration, trust telemetry, SLO/access/evidence policy, mesh certification, and conservative `/platform/capabilities` promotion only after proof. |
| Gateway and Workbench realization | Gateway contract tests, Workbench API abstraction tests, browser tests, canonical front-office runtime proof, and no UI-local AI, guardrail, evidence, or review-state invention. |
| Canonical automation | Platform canonical contract/invariant updates, `RFC27_ADVISORY_COPILOT_CANONICAL`, Workbench live validation, `npm run live:stack:up:validate` proof, and lowest-useful-layer regression tests for every live defect. |
| Documentation and commercial proof | README/wiki/supported-features updates only after implementation evidence; business-facing wording must explain advisor value, review posture, blockers, and next actions without raw prompt, provider, trace, correlation, or internal run-mechanics leakage. |

## No Platform Change Rationale

The current gap is not missing platform automation. The current gap is disciplined copilot product
definition inside `lotus-advise`, strict `lotus-ai` workflow-pack ownership, and strict
Gateway/Workbench realization in subsequent RFC-0027 slices:

1. creating first-class copilot models instead of stretching proposal narrative or memo responses,
2. preserving source authority and source-readiness gaps without inventing client, portfolio,
   proposal, policy, memo, cockpit, report, operations, or model-risk facts,
3. preventing premature copilot data-product, Gateway, Workbench, demo, report, CRM, OMS,
   client-ready, or full RFC-0028 claims,
4. keeping guardrail, unsupported-evidence, review, redaction, and retention semantics
   backend-owned,
5. using platform-owned validation, mesh, wiki, runtime, workflow-security, and CI controls instead
   of adding copilot-only scaffolding.

Those risks are better controlled by RFC-0027 Slice 0 and Slice 1 source truth, focused docs
contract tests, repo-native gates, and subsequent implementation tests than by adding a new
platform automation surface now.

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Stranded-truth reconciliation | `git fetch origin --prune` and `git branch -r --no-merged origin/main` returned no unmerged remote branches before RFC-0027 implementation began across `lotus-advise`, `lotus-gateway`, `lotus-workbench`, and `lotus-platform`. |
| Platform automation review | Reviewed `lotus-platform` service scaffolding, OpenAPI conformance, API vocabulary, workflow security, workflow action runtime validation, domain-data-product onboarding, trust telemetry, mesh certification, docs/wiki synchronization, canonical front-office runtime routing, and heartbeat/async guidance relevant to copilot execution. |
| Repo-native gate review | Reviewed `lotus-advise` Makefile gates, OpenAPI/vocabulary/no-alias controls, docs contract tests, capabilities posture, live runtime evidence helpers, data-product/trust telemetry contracts, and RFC-0023/RFC-0024/RFC-0025/RFC-0026 evidence patterns. |
| No one-off scaffold decision | Recorded explicit rejection of local-only copilot certification, mesh, prompt registry, workflow-pack registry, OpenAPI, telemetry, wiki, UI, report, archive, operations, model-risk, and canonical seed scaffolds before the copilot contract exists. |
| Next-slice readiness | RFC-0027 may proceed to Slice 2 cleanup and structure using existing platform and repo-native gates. |

## Wiki and README Decision

Wiki source and the RFC index are updated because RFC-0027 implementation status and product-roadmap
truth changed. README does not change in this slice because command surfaces, runtime behavior, and
supported feature entrypoints did not change.
