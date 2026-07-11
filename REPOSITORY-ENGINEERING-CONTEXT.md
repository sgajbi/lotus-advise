# Repository Engineering Context

This file provides repository-local engineering context for `lotus-advise`.

For platform-wide truth, read:

1. `../lotus-platform/context/LOTUS-QUICKSTART-CONTEXT.md`
2. `../lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
3. `../lotus-platform/context/CONTEXT-REFERENCE-MAP.md`

## Repository Role

`lotus-advise` is the advisory workflow and proposal simulation service.

It owns advisor-led proposal lifecycle and recommendation-oriented execution readiness behavior.

## Business And Domain Responsibility

This repository owns:

1. advisor-led proposal simulation,
2. proposal lifecycle state,
3. advisory approvals and consent-related workflow behavior,
4. advisory execution readiness,
5. source-owned tactical house-view affected cohorts for bank-authored house-view instructions and
   caller-supplied source-backed candidate portfolios.

It does not own discretionary portfolio-management operations; those belong to `lotus-manage`.

## Current-State Summary

Current repository posture:

1. `lotus-advise` is now scoped to advisory-only workflows after the split from `lotus-manage`,
2. runtime smoke and production-profile guardrail validation are part of the real CI contract,
3. canonical upstream integration with `lotus-core` and `lotus-risk` matters for truthful proposal behavior,
4. proposal simulation, artifact, workspace, replay, and lifecycle surfaces now expose persisted backend-owned `proposal_decision_summary` and `proposal_alternatives`,
5. RFC-0023 advisor-review proposal narrative is supported in the proposal artifact,
   proposal-version review/replay, reviewed report-request package propagation, and downstream
   `lotus-report`/`lotus-render` advisor-use report rendering path, with `lotus-archive`
   support-safe archive metadata summaries for rendered advisor-use portfolio-review artifacts;
   `lotus-gateway` now exposes product-facing reviewed-narrative posture through canonical
   `lotus-advise` APIs and `lotus-workbench` renders the Gateway-backed advisor-use proposal
   narrative posture. `ProposalNarrativeEvidence:v1` is declared as a governed advisor-review
   evidence product with repo-native trust telemetry and `/platform/capabilities` reviewed
   narrative evidence feature/workflow promotion. Live runtime evidence now validates stateful
   advisor-review narrative requests, immutable read, non-persistent regeneration, advisor-use
   review, reviewed report-package request, replay evidence, deterministic guardrail-failure
   reproduction, and optional AI-assisted narrative validation when enabled. Canonical Workbench
   proof now covers `proposal.narrative_posture`. Slice 13/14 hardening records that even a clean
   advisor-review narrative release request cannot return `APPROVED_FOR_CLIENT_READY`.
   Client-ready commentary, compliance-review and client-draft narrative, and client communication
   remain gated. Standalone proposal-version
   narrative read and non-persistent regeneration APIs are supported for advisor-review posture.
   Historical Slice 0-11 audit wording is preserved only as audit context. Slice 12 closed the
   advisor-review Workbench canonical proof path and Slice 13/14 hardened the client-ready approval
   boundary; client-ready narrative, compliance-review narrative, client-draft narrative,
   client-ready publication, and external client communication remain gated future scope rather
   than supported RFC-0023 closure claims,
6. RFC-0024 advisor proposal memo support now includes advisor-use report/render/archive
   realization, review-gated AI commentary, Gateway/Workbench product realization,
   memo-specific commercial support material, and live-suite implementation proof: Advise
   requires memo hash continuity and `APPROVE_FOR_ADVISOR_USE` review before sending a typed memo
   package to `lotus-report` or a bounded memo evidence packet to `lotus-ai`
   `proposal_memo_commentary.pack@v1`; memo lineage records returned report/render/archive refs and
   append-only AI lineage. Gateway now routes canonical Advise memo endpoints, and Workbench
   consumes Gateway/BFF-only memo posture, projection, report-package, archive-ref, AI-commentary,
   lineage, replay, degraded, and blocked states without local memo inference. The memo commercial
   guide gives sales/pre-sales a claim-controlled one-pager, demo notes, API examples, architecture
   flow, operator guidance, and RFP-safe wording for the implemented advisor-use posture. The
   governed live runtime evidence bundle now emits `proposal_memo` proof for Advise memo APIs, the
   stateful source dependency path, advisor projection, advisor-use report/render/archive request
   posture, review-gated AI commentary, lineage, replay hashes, degraded report posture, and
   stale-hash/client-ready blocked paths. `AdvisoryProposalMemoEvidencePack:v1` is now an active
   advisor-use data product with current repo-native trust telemetry, `/platform/capabilities`
   feature/workflow posture, and platform SLO/access/evidence-policy support. Final hardening adds
   canonical `PB_SG_GLOBAL_BAL_001` Workbench proof that the advisor journey and
   `proposal.memo_evidence_pack` panel are Gateway-backed. RFC-0024 is closed for advisor-use memo evidence with durable README/wiki/supported-features/RFC/context/domain-product/trust telemetry truth updated.
   Full RFC-0028 bank-demo/RFP package claims remain gated, and client-ready memo publication remains gated,
7. RFC-0025 enterprise policy-pack implementation is closed for advisor/compliance policy evidence.
   Slice 3 declared `AdvisoryPolicyEvaluationRecord:v1` as a proposed, blocked data product with trust telemetry and
   platform catalog posture. Slice 4 adds `rfc0025.policy-source-readiness.v1` to proposal evidence
   bundles so future policy evaluation consumes explicit `lotus-core`, `lotus-risk`, and
   `lotus-advise` source-readiness sections rather than inferring or defaulting missing source
   facts. Slice 5 adds `rfc0025.policy-pack-catalog.v1`, reference-pack list/detail/validate/
   activate APIs, schema/content validation, content hashes, maker-checker activation, and audit
   events for `GLOBAL_PRIVATE_BANKING_BASELINE` and `SG_PRIVATE_BANKING_REFERENCE`. Slice 6 adds
   the internal `rfc0025.policy-evaluation-engine.v1` applicability and rule-evaluation engine for
   active policy packs, including source-backed material rule posture for source readiness,
   mandate, product eligibility, complex-product disclosure/consent, best-interest cost evidence,
   and conflict/product-document review. Slice 7 adds internal
   `rfc0025.policy-evaluation-persistence.v1` finalized policy evaluation records with
   policy/source/evaluation hashes, per-rule hashes, source gaps, approval dependencies,
   disclosure and consent requirements, replay metadata, duplicate prevention, idempotent replay,
   and append-only review/sign-off/report-archive events. Slice 8 exposes certified Advise policy
   evaluation create/read/replay/event/lineage/review-queue/sign-off source-package APIs and
   OpenAPI documentation. Slice 9 adds Advise-owned policy workflow projection and sign-off
   decision recording over finalized records, including approval dependencies, disclosure and
   consent requirements, conflict posture, SLA aging, maker-checker enforcement, source-hash
   validation, and append-only sign-off events. Slice 10 adds Advise-owned policy report-package
   realization for signed-off policy evaluations: typed `lotus-report` handoff, returned
   report/render/archive refs in policy lineage, idempotent replay, and fail-closed client-ready
   document handling. Slice 11 adds Advise-owned AI policy-evidence consumption: redacted bounded
   policy evidence packets to `policy_evidence_summary.pack@v1`, forbidden-action rejection,
   deterministic unavailable posture, prompt/output lineage, human review, non-authoritative AI
   posture, and client-ready blocked lineage. Slice 12 adds Gateway and Workbench product
   realization: Gateway routes canonical Advise policy-pack/evaluation BFF APIs, and Workbench
   consumes Gateway-only policy review queue, selected evaluation detail, sign-off source package,
   workflow posture, and bounded request-more-evidence actions without local policy inference.
   Slice 13 adds policy-pack-specific commercial support material with claim-controlled one-pager
   language, demo notes, API examples, architecture flow, operator guidance, security posture, and
   RFP-safe wording. Slice 14 adds live-suite policy implementation proof: `proposal_policy` covers
   Advise policy evaluation APIs, SG reference-pack hashes, source refs and gaps, requirement
   counts, workflow and sign-off posture, report/render/archive refs or degraded reason, bounded AI
   evidence, lineage, replay hashes, and stale-hash/client-ready/forbidden-AI blocked paths.
   Slice 15 hardens the second-last review boundary by centralizing policy-pack supportability
   posture in `src/core/policy_packs/supportability.py` and removing stale earlier-slice
   Gateway/Workbench/report-handoff unsupported claims from code, OpenAPI/schema examples, and
   tests.
   Slice 16 promotes `AdvisoryPolicyEvaluationRecord:v1` as an active advisor/compliance policy
   evidence product with current trust telemetry, `/platform/capabilities` feature/workflow
   posture, platform SLO/access/evidence-policy support, and durable README/wiki/RFC/context/
   domain-product/trust telemetry closure truth. Runtime policy catalog/evaluation state is now
   composed through policy repository ports and backed by the `policy_packs` Postgres migration
   namespace for records, audit events, activation state, and idempotency maps. Completed
   approval/waiver authority, completed sign-off authority, client-ready policy publication,
   external client communication, and full RFC-0028 bank-demo/RFP package claims remain gated,
8. RFC-0026 advisor cockpit first-wave scope is implemented for source-owned Advise evidence and
   cross-repo product consumption: the dedicated `src/core/advisor_cockpit/` package owns action
   construction, source-read-model aggregation, SLA/acknowledgement rules, supportability, and API
   DTO projection; Advise exposes certified action, snapshot, supportability, and acknowledgement
   routes; Gateway and Workbench consume those contracts; canonical `PB_SG_GLOBAL_BAL_001` proof is
   present; `AdvisorCockpitOperatingSnapshot:v1` and `AdvisoryActionItemRegister:v1` are active
   data products with trust telemetry and `/platform/capabilities` feature/workflow posture.
   Public Advisor Cockpit caller and owner role vocabulary uses `PORTFOLIO_MANAGER` for
   portfolio-management owned actions; the legacy `DPM_OWNER` caller alias is retired from OpenAPI,
   API vocabulary inventory, and request validation.
   Client-ready publication, external client communication, CRM system-of-record behavior, OMS
   order/fill/settlement lifecycle, completed policy approval authority, and full RFC-0028
   demo/RFP package claims remain gated,
9. RFC-0028 bank-demo proof is implemented through the Advise scenario contract,
   `AdvisorySupportedClaimRegister:v1`, sanitized proof-pack capture, Gateway publication,
   Platform canonical scenario/panel registration, and Workbench `advisory.bank_demo_proof`
   evidence. Canonical `PB_SG_GLOBAL_BAL_001` validation records
   `BANK_DEMO_PROOF_PACK_CREATED` and proves blocked client-ready publication posture without
   claiming external client communication, OMS/order/fill/settlement, approval authority, or full
   RFP/demo collateral readiness. Slice 9 adds
   `AdvisoryJourneyIntegrationProofSummary:v1` to the backend proof pack so AI/model-risk,
   policy, and advisor-cockpit boundary evidence is reviewed as source-owned proof without raw
   prompt/source leakage or unsupported approval/client-ready claims. Slice 10 adds
   `AdvisoryCommercialMaterialPack:v1`,
   `docs/commercial/RFC-0028-bank-demo-client-proof-materials.md`, and
   `commercial_rfp_security_material_available` for claim-controlled product, RFP, security,
   architecture, ROI, demo, feature-matrix, boundary, proof-guide, and operator material while
   preserving blocked client-ready, external-communication, legal/regulatory, bank-attestation,
   completed-sign-off, and OMS/order/fill/settlement claims. Slice 11 moves runtime posture into
   `src/core/bank_demo_proof/runtime_posture.py`, records bounded `latency_ms`, rejects runtime
   proof URLs with credentials/query/fragment material, and redacts sensitive runtime summaries
   before proof artifacts can carry security/latency evidence with proof marker
   `RFC0028_RUNTIME_SECURITY_POSTURE_HARDENED`. Slice 13/14 closes final implementation proof and
   hardening through PR #213, `src/core/bank_demo_proof/artifact_refs.py`, local artifact-reference
   normalization, safe HTTP 422 validation error responses that do not echo rejected sensitive
   input, targeted proof tests, `make check`, PR Merge Gate, and Main Releasability Gate run
   `26573760885` on merge `a99474e5457dcdd4c87e79faf83bc8f64580544b`. Slice 15/16 closes durable
   RFC, README, wiki, repository-context, supported-features, and post-completion communication
   truth through `lotus-platform` PR #369 at `26d74e65e231ac3d62457187c6eb7f787a4d9f88`,
   Main Releasability Gate run `26574820026`, and
   `lotus-platform/thought-leadership/linkedin/drafts/LI-2026-05-28-043-demo-proof-should-show-the-boundary.md`.
   RFC-0028 is implemented for repeatable bank-demo proof and claim-controlled commercial
   material; client-ready publication, external client communication, bank-specific attestations,
   legal/regulatory advice, completed sign-off/approval, and OMS/order/fill/settlement remain
   unpromoted,
10. live operator evidence validates decision-summary and proposal-alternatives posture across canonical and degraded runtime paths,
11. upstream service consumption is classified under RFC-0082 in `docs/architecture/RFC-0082-upstream-contract-family-map.md`,
12. repo-native CI is already aligned to explicit lane expectations,
13. RFC-0086 repo-native declaration onboarding now covers the advisory proposal lifecycle product,
   proposal narrative evidence product, and a bounded tactical house-view affected-cohort product
   in `contracts/domain-data-products/`, with explicit upstream dependencies,
14. RFC-0087 trust telemetry proof for `AdvisoryProposalLifecycleRecord`, RFC-0023 trust telemetry
   proof for `ProposalNarrativeEvidence`, and RFC-0026 trust telemetry proof for the advisor
   cockpit operating snapshot and action-item register now live under `contracts/trust-telemetry/`
   and are validated by `tests/unit/test_trust_telemetry.py` against the platform trust telemetry
   validator when `lotus-platform` is available,
15. the advisory workspace rationale path now uses the explicit `lotus-ai` workflow-pack execution
   seam for the `workspace_rationale.pack` family, preserves bounded run posture in the advisory
   response, and exposes a separate bounded review-action pass-through that retains Lotus AI
   lineage truth,
16. execution handoff, status, and delivery projections carry explicit ownership-boundary evidence
   so advisory posture cannot be confused with downstream execution system-of-record truth,
17. `POST /advisory/proposals/idea-intake` is implemented as a source-safe `lotus-idea`
   conversion-intent route foundation. It is not certified as proposal realization, does not
   persist proposal lifecycle records, does not run suitability, does not authorize client
   publication, and must not be listed as a supported feature until the downstream realization
   blockers are closed with runtime evidence.

## Architecture And Module Map

Primary areas:

1. `src/`
   advisory APIs, workflow logic, and supporting modules.
2. `scripts/`
   dependency-health, runtime smoke, OpenAPI, vocabulary, and governance scripts.
3. `docs/`
   advisory standards and workflow documentation.
4. `tests/`
   unit, integration, and e2e validation.
5. `wiki/`
   canonical authored source for GitHub wiki publication and advisory operator onboarding summaries.
6. `contracts/domain-data-products/`
   repo-native producer and consumer declarations for governed advisory products and dependencies.
7. `contracts/trust-telemetry/`
   repo-native RFC-0087 trust telemetry fixtures for governed advisory products.

## Runtime And Integration Boundaries

Runtime model:

1. FastAPI advisory service,
2. depends on `lotus-core` and `lotus-risk`,
3. consumed through `lotus-gateway` for integrated product flows.

Boundary rules:

1. advisor-only workflows belong here,
2. management-only workflows belong in `lotus-manage`,
3. proposal simulation must remain aligned with authoritative upstream data and risk posture,
4. Lotus Core stateful context must reject returned portfolio, positions, cash, or resolved-as-of
   identity that conflicts with the requested source identity before constructing or caching
   advisory snapshots,
5. Lotus Core stateful context, enrichment, taxonomy, instrument, price, and FX caches must use
   the shared semantic cache identity from
   `src/integrations/lotus_core/stateful_context_cache_identity.py`. Keys include sanitized
   query/control-plane source URL, `ENVIRONMENT`, `LOTUS_ADVISE_TENANT_ID` when configured,
   advisory simulation contract version, portfolio, as-of, mandate, benchmark, reporting currency,
   look-through/allocation/risk dimensions, and lookup-specific identifiers; current unsupported
   dimensions remain explicit default dimensions rather than omitted key parts,
6. Lotus Core source provenance is part of advisory result lineage. Stateful context must preserve
   upstream portfolio and market-data snapshot identity, source version, event or batch refs, source
   hash, valuation timestamp, freshness posture, and contract version as typed provenance on the
   resolved context, advisory snapshots, and proposal lineage without storing raw source payloads.
   Conflicting source snapshot or provenance values must fail closed before advisory snapshot
   construction, caching, persistence, or replay,
7. Lotus Core source-derived FX rates must be finite, strictly positive, and as-of eligible before
   advisory valuation. Invalid explicit rates or source ratios fail closed with
   `LOTUS_CORE_STATEFUL_FX_INVALID`; missing eligible rates remain data-quality evidence rather
   than fabricated conversion inputs. Inverse-pair valuation is supported only from a valid positive
   inverse rate,
8. Lotus Core stateful context must account for source-row completeness before advisory snapshot
   construction. Required positions, cash, price, and FX source rows cannot silently disappear:
   malformed or incomplete required rows fail closed with
   `LOTUS_CORE_STATEFUL_SOURCE_INCOMPLETE`. Optional enrichment and classification taxonomy gaps
   remain explicit degraded source-completeness evidence on resolved context, advisory snapshots,
   and proposal lineage without storing raw source payloads,
9. decision-summary, proposal-alternatives generation, ranking, selection, approval-requirement, and material-change semantics are backend-owned contracts and must not be generated, reranked, or re-inferred in UI or support layers,
10. proposal alternatives must remain anchored to canonical `lotus-core` simulation and `lotus-risk` enrichment rather than local duplicated calculations,
11. tactical house-view affected cohorts must remain bounded to supplied source-backed candidates,
   preserve source refs, and must not discover the global portfolio universe or open DPM campaigns,
12. execution handoff, status, and delivery surfaces must preserve the boundary that `lotus-advise`
   records advisory posture while downstream providers remain execution systems of record,
13. REST/OpenAPI remains the canonical integration contract; gRPC is not justified for current advisory upstream calls,
14. runtime smoke should honor injected CI DSNs and canonical service identities rather than stale local assumptions,
15. `lotus-idea` proposal-intake route foundation must remain source-safe: Advise acknowledges only
   the handoff envelope and retains proposal, suitability, approval, publication, and execution
   authority until a later certified realization slice implements those controls,
16. outbound `lotus-report` and `lotus-ai` calls must fail closed when tenant or actor identity is
   missing, malformed, over-length, or control-character-bearing; do not reintroduce synthetic
   production defaults such as a hardcoded tenant or service actor,
17. outbound `lotus-report` calls must require source-derived as-of date, reporting currency, and
   jurisdiction/booking-center metadata; current-date, USD, and SG fallbacks are not production
   source truth,
18. unavailable `lotus-risk` authority must always carry degraded evidence with a stable reason
   code; do not allow `risk_authority="unavailable"` with `degraded=false`.
19. advisor memo and policy sign-off report packages must not project archive-ready status from
    accepted, running, missing-status, malformed-status, or failed status lookups; terminal
    readiness requires `lotus-report` archive evidence and all non-terminal status must preserve
    the report job id for operator recovery.
20. external service adapters for `lotus-core`, `lotus-risk`, `lotus-report`, and `lotus-ai`
    must keep versioned consumer-contract fixtures under
    `tests/fixtures/external-adapter-contracts/` and pass `make external-adapter-contracts`.
    The lane must cover valid responses, malformed JSON, missing fields, portfolio/as-of identity
    mismatch, partial data, auth failures, timeouts, retry or bounded non-retry posture, duplicate
    or idempotency behavior, provider error mapping, and raw-payload/secret non-leakage.

## Repo-Native Commands

Use these commands as the primary local contract:

1. install
   `make install`
2. fast local gate
   `make check`
3. PR-grade local gate
   `make ci`
4. feature-lane local gate
   `make ci-local`
5. Docker parity
   `make ci-local-docker`
6. run locally
   `make run`
7. repo-native domain product gate
   `make domain-data-products-gate`
8. quality evidence freshness gate
   `make quality-baseline-check`
9. live demo certification evidence
   `make demo-certification-live`

## Validation And CI Expectations

`lotus-advise` uses explicit CI lanes:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

Important validation expectations:

1. dependency health, OpenAPI, vocabulary, and no-alias governance are active,
   and direct dependency freshness is evaluated against the repository-supported Python 3.11
   runtime rather than an incompatible package release that only supports a newer Python line,
   while routine Dependabot version-update PRs are paused with
   `open-pull-requests-limit: 0` so dependency suggestions are handled through deliberate
   repo-native refresh, security review, and PR validation instead of noisy bot branches. The API
   vocabulary gate recursively rejects placeholder-shaped generated examples such as `sample_text`,
   `sample_key`, `STANDARD_TEXT`, `STANDARD_ITEM`, `ENTITY_001`, and `example_*`; generated
   inventory examples must come from source-authored metadata or the governed deterministic
   fallback policy. OpenAPI display enrichment remains available for Swagger readability, but the
   OpenAPI quality gate treats generated operation summaries, descriptions, inferred tags, and
   generic default error responses as missing public-route contract truth,
2. `make external-adapter-contracts` is the named consumer-contract lane for external adapters and
   is included in `make check`; it prevents fake-only adapter tests from drifting away from
   provider-compatible fixtures and adversarial failure-mode evidence,
3. migration smoke, coverage, Docker build, Postgres runtime smoke, and production-profile guardrail validation are part of the merge gate,
4. advisory workflow changes should be validated against canonical upstream posture,
5. live runtime evidence should prove decision-summary and proposal-alternatives posture on canonical and degraded paths when advisory proposal behavior changes materially,
6. `make demo-certification-live` is the repo-native app-level live certification command; it writes
   machine-readable evidence under `output/demo-certification/`, validates deterministic synthetic
   scenarios, route-safety posture, required `/platform/capabilities` feature/workflow truth, and
   domain assertions, and is wired into the scheduled/manual Postgres runtime workflow as uploaded
   evidence rather than a PR-blocking static gate,
7. committed quality Markdown intentionally omits volatile branch/head metadata; exact Git identity belongs to Git history and GitHub Actions run metadata, while `make quality-baseline-check` enforces non-timestamp report freshness.

## Standards And RFCs That Govern This Repository

Most relevant current governance:

1. `../lotus-platform/rfcs/RFC-0066-lotus-advise-to-lotus-advise-and-lotus-manage-split.md`
2. `../lotus-platform/rfcs/RFC-0067-centralized-api-vocabulary-inventory-and-openapi-documentation-governance.md`
3. `../lotus-platform/rfcs/RFC-0072-platform-wide-multi-lane-ci-validation-and-release-governance.md`
4. `../lotus-platform/rfcs/RFC-0073-lotus-ecosystem-engineering-context-and-agent-guidance-system.md`
5. `../lotus-platform/rfcs/RFC-0082-lotus-core-domain-authority-and-analytics-serving-boundary-hardening.md`
6. `docs/architecture/RFC-0082-upstream-contract-family-map.md`
7. `docs/architecture/RFC-0086-repo-native-domain-product-onboarding.md`
8. `docs/standards/`

## Known Constraints And Implementation Notes

1. advisory and management boundaries must remain explicit after the repository split,
2. runtime smoke orchestration is operationally important here because CI includes real environment behavior, not just unit logic,
3. proposal behavior must not drift away from upstream data and risk authorities,
4. persisted proposal versions are expected to preserve the exact decision summary and proposal alternatives used by artifact, replay, workspace, and operator evidence surfaces,
5. proposal alternatives remain opt-in, bounded, and dependent on canonical upstream authorities; unsupported objectives must reject explicitly rather than degrade into guessed behavior,
6. restricted-product alternatives remain deferred until canonical eligibility evidence is available,
7. advisory stateful context operational reads, advisory simulation execution, and enrichment fallback labels remain RFC-0082 watchlist surfaces,
8. RFC-0086 consumer declarations should stay conservative and only reference upstream products
   already approved and truthfully mapped in the current platform catalog,
9. advisory lifecycle changes should update both code and repo context in the same slice,
10. tactical house-view cohort changes should preserve the Advise/Manage boundary: Advise owns
   source cohort evaluation; Manage owns DPM workflows, campaigns, policies, and evidence,
11. repo-local `wiki/` content should stay concise, operator-focused, and derived from repo truth rather
   than duplicating the full `docs/` tree.

## Context Maintenance Rule

Update this document when:

1. advisory workflow ownership or lifecycle scope changes,
2. repo-native commands or runtime smoke behavior changes,
3. upstream integration posture changes materially,
4. guardrail or production-profile expectations change,
5. RFC-0082 contract-family classification changes,
6. current-state rollout posture changes,
7. wiki ownership or publication workflow changes.

## Cross-Links

1. `../lotus-platform/context/LOTUS-QUICKSTART-CONTEXT.md`
2. `../lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
3. `../lotus-platform/context/CONTEXT-REFERENCE-MAP.md`
4. `../lotus-platform/context/Repository-Engineering-Context-Contract.md`
5. [Lotus Developer Onboarding](../lotus-platform/docs/onboarding/LOTUS-DEVELOPER-ONBOARDING.md)
6. [Lotus Agent Ramp-Up](../lotus-platform/docs/onboarding/LOTUS-AGENT-RAMP-UP.md)
