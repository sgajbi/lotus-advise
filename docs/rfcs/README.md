# RFC Index

Standards for all current and future RFCs:
- `docs/rfcs/RFC-CONVENTIONS.md`

Historical closed work-to-be-done ledger:
- `docs/rfcs/WTBD.md`

Execution rule:
- new advisory crown-jewel work must be represented as RFC slices, acceptance criteria, and
  closure evidence, not as new WTBD entries. The WTBD ledger is retained only as closed historical
  context for work already folded back into RFC planning.

Governance boundary:
- Service-specific implementation RFCs belong in this repository.
- Cross-cutting platform and multi-service RFCs belong in `https://github.com/sgajbi/lotus-platform`.

This index is the source of truth for RFC disposition in `lotus-advise`.

## Active RFCs

The active RFC set lives in a single flat sequence under `docs/rfcs/`.

The sequence is organized to read in implementation order:
- platform and runtime foundations first,
- advisory workflow and lifecycle capabilities next,
- future advisory expansion slices after the implemented core.

| RFC | Title | Status | Disposition | Depends On | File |
| --- | --- | --- | --- | --- | --- |
| RFC-0001 | PostgreSQL-Only Production Mode Cutover | SUPERSEDED | Historical traceability only; superseded by RFC-0005 | - | `docs/rfcs/RFC-0001-postgres-only-production-mode-cutover.md` |
| RFC-0002 | Automated Release Notes and Lightweight Release Process | PROPOSED | Deferred / low priority | RFC-0001 | `docs/rfcs/RFC-0002-automated-release-notes-and-release-process.md` |
| RFC-0003 | Advisory Proposal Workflow Coverage Hardening (Approval Chain Paths) | IMPLEMENTED | Active | RFC-0013 | `docs/rfcs/RFC-0003-advisory-proposal-workflow-coverage-hardening.md` |
| RFC-0004 | Iterative Advisory Proposal Workspace Contract | IMPLEMENTED | Active | RFC-0013, RFC-0003 | `docs/rfcs/RFC-0004-iterative-advisory-proposal-workspace-contract.md` |
| RFC-0005 | Advisory PostgreSQL Runtime and Persistence Cutover | IMPLEMENTED | Active runtime persistence source of truth | RFC-0004, RFC-0006 | `docs/rfcs/RFC-0005-postgres-only-advisory-runtime-hard-cutover.md` |
| RFC-0006 | lotus-advise Target Operating Model and Integration Architecture | IMPLEMENTED | Active architecture source of truth | RFC-0013, RFC-0003, RFC-0004 | `docs/rfcs/RFC-0006-lotus-advise-target-operating-model-and-integration-architecture.md` |
| RFC-0007 | Advisory Proposal Simulation MVP (Manual Trades + Cash Flows) | IMPLEMENTED | Active | - | `docs/rfcs/RFC-0007-advisory-proposal-simulate-mvp.md` |
| RFC-0008 | Advisory Proposal Auto-Funding (FX Spot Intents + Dependency Graph) | IMPLEMENTED | Active | RFC-0007 | `docs/rfcs/RFC-0008-advisory-proposal-auto-funding.md` |
| RFC-0009 | Drift Analytics for Advisory Proposals (Before vs After vs Reference Model) | IMPLEMENTED | Active | RFC-0007 | `docs/rfcs/RFC-0009-drift-analytics.md` |
| RFC-0010 | Suitability Scanner v1 for Advisory Proposals | IMPLEMENTED | Active | RFC-0007 | `docs/rfcs/RFC-0010-suitability-scanner-v1.md` |
| RFC-0011 | Advisory Proposal Artifact | IMPLEMENTED | Active | RFC-0007, RFC-0008, RFC-0009, RFC-0010 | `docs/rfcs/RFC-0011-proposal-artifact.md` |
| RFC-0012 | Advisory Workflow Gates and Next-Step Semantics | IMPLEMENTED | Active | RFC-0007 | `docs/rfcs/RFC-0012-advisory-workflow-gates.md` |
| RFC-0013 | Advisory Proposal Persistence, Workflow Lifecycle, and Audit Model | IMPLEMENTED | Active lifecycle/audit source of truth | RFC-0004, RFC-0005, RFC-0006, RFC-0007 | `docs/rfcs/RFC-0013-proposal-persistence-workflow-lifecycle.md` |
| RFC-0014 | Data Quality, Snapshots, and Replayability | DRAFT | Active future work | RFC-0007, RFC-0011, RFC-0013 | `docs/rfcs/RFC-0014-data-quality-snapshots-replayability.md` |
| RFC-0015 | Jurisdiction and Policy Packs | DRAFT | Active future work | RFC-0010, RFC-0011, RFC-0012, RFC-0013 | `docs/rfcs/RFC-0015-jurisdiction-policy-packs.md` |
| RFC-0016 | Costs, Fees, and Transaction Frictions v1 | DRAFT | Active future work | RFC-0007, RFC-0008, RFC-0011, RFC-0014 | `docs/rfcs/RFC-0016-costs-fees-frictions-v1.md` |
| RFC-0017 | Execution Integration Interface | DRAFT | Active future work | RFC-0011, RFC-0012, RFC-0013 | `docs/rfcs/RFC-0017-execution-integration-interface.md` |
| RFC-0018 | Monitoring, Surveillance, and Post-Trade Controls | DRAFT | Active future work | RFC-0015, RFC-0017 | `docs/rfcs/RFC-0018-monitoring-surveillance-post-trade-controls.md` |
| RFC-0019 | Authoritative Context, Durable Runtime, and Workspace Closure | IMPLEMENTED | Active authoritative runtime closure | RFC-0004, RFC-0005, RFC-0006, RFC-0011, RFC-0013, RFC-0014, RFC-0017 | `docs/rfcs/RFC-0019-authoritative-context-runtime-and-workspace-closure.md` |
| RFC-0020 | Canonical Allocation and Risk Lens Convergence for Proposals | IMPLEMENTED | Active canonical allocation and risk-lens source of truth | RFC-0006, RFC-0007, RFC-0011, RFC-0014, RFC-0019 | `docs/rfcs/RFC-0020-canonical-allocation-and-risk-lens-convergence.md` |
| RFC-0021 | Proposal Decision Summary and Enterprise Suitability Policy | IMPLEMENTED | Active backend-owned decision summary and enterprise suitability source of truth | RFC-0006, RFC-0010, RFC-0012, RFC-0013, RFC-0015, RFC-0019, RFC-0020 | `docs/rfcs/RFC-0021-proposal-decision-summary-and-enterprise-suitability-policy.md` |
| RFC-0022 | Proposal Alternatives and Portfolio Construction Workbench | IMPLEMENTED | Active backend-owned proposal alternatives and portfolio-construction source of truth | RFC-0006, RFC-0007, RFC-0008, RFC-0009, RFC-0010, RFC-0013, RFC-0016, RFC-0019, RFC-0020, RFC-0021 | `docs/rfcs/RFC-0022-proposal-alternatives-and-portfolio-construction-workbench.md` |
| RFC-0023 | Grounded Advisory AI Narrative and Client-Ready Proposal Commentary | IMPLEMENTED for advisor-review narrative evidence; client-ready scope remains gated | Active advisor-review narrative evidence source of truth; Slices 0-10 complete source mapping, platform-scaffolding review, cleanup/structure, narrative contract baseline, data-product/supportability baseline, deterministic advisor-review artifact-path narrative, policy/disclosure/guardrail baseline, AI-assisted draft adapter baseline, proposal-version narrative review/replay baseline, decision-summary/alternatives/approval/limitation narrative integration, and certified API/OpenAPI baseline; Slice 10B closes standalone proposal-version narrative read and non-persistent regeneration APIs; Slice 11A adds reviewed narrative package propagation into report-request evidence; Slices 11B/11C close `lotus-report` package consumption and `lotus-render` portfolio-review advisory narrative rendering; Slice 11D closes `lotus-archive` support-safe reviewed narrative artifact summary storage; Slice 11E closes `lotus-gateway` product-facing reviewed-narrative posture and `lotus-workbench` Gateway-backed advisor-use proposal posture; Slice 11F promotes advisor-review narrative evidence as `ProposalNarrativeEvidence:v1` with trust telemetry, platform catalog/certification, and `/platform/capabilities` reviewed narrative evidence posture; Slice 12 adds stateful live narrative proof, deterministic guardrail-failure reproduction, optional AI-assisted validation where enabled, and governed Workbench `proposal.narrative_posture` screenshot proof; Slice 13/14 hardens the closure boundary so even clean advisor-review narratives cannot return `APPROVED_FOR_CLIENT_READY`; compliance-review, client-draft, client-ready publication, and client communication remain gated future scope | RFC-0006, RFC-0011, RFC-0013, RFC-0014, RFC-0015, RFC-0019, RFC-0020, RFC-0021, RFC-0022 | `docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md` |
| RFC-0024 | Advisor Proposal Memo and Evidence Pack | IMPLEMENTED for advisor-use proposal memo evidence; client-ready memo publication remains gated | Active advisor-use memo evidence source of truth; Slices 0-8 close source mapping, platform-scaffolding review, cleanup/structure, proposed/blocked data-product posture, memo source-readiness evidence, deterministic memo building, persistence/replay/idempotency/audit, certified Advise memo APIs, and memo-critical suitability/product/cost/disclosure/conflict enrichment. Slice 9 implements advisor-use report/render/archive realization. Slice 10 implements review-gated advisor-use AI commentary through `proposal_memo_commentary.pack@v1`. Slice 11 implements Gateway routing through canonical Advise memo endpoints and Workbench Gateway/BFF-only memo posture, projection, report-package, archive-ref, AI-commentary, lineage, replay, degraded, and blocked states. Slice 12 implements memo-specific commercial support material in `docs/commercial/RFC-0024-advisor-proposal-memo-commercial-support.md`, including claim-controlled one-pager language, demo notes, API examples, architecture flow, operator guidance, and RFP-safe wording. Slice 13 adds memo proof to the live runtime evidence bundle. Slice 14 promotes `AdvisoryProposalMemoEvidencePack:v1` as an active advisor-use data product with current trust telemetry, `/platform/capabilities`, and platform SLO/access/evidence-policy posture. Slice 15 adds canonical `PB_SG_GLOBAL_BAL_001` Workbench proof for the advisor journey and `proposal.memo_evidence_pack` panel. Slice 16 closes durable truth across README, wiki source, supported-features, RFC status, repo context, domain-product declaration, trust telemetry, and proof summaries. Slice 17 adds an employer-safe post-completion LinkedIn draft and content-ledger update in `lotus-platform`. Full RFC-0028 bank-demo/RFP package claims and client-ready memo claims remain gated. WTBD is closed historical context only. | RFC-0006, RFC-0011, RFC-0013, RFC-0019, RFC-0020, RFC-0021, RFC-0022, RFC-0023 | `docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md` |
| RFC-0025 | Enterprise Suitability and Best-Interest Policy Packs | DRAFT - GOLD-STANDARD IMPLEMENTATION PLAN | Active crown-jewel feature roadmap; RFC is the execution source and WTBD is closed historical context only. Slice 0 tightens pre-implementation policy-pack decisions; Slice 1 records the platform-scaffolding review and no-platform-change decision before policy domain work; Slice 2 cleans the current suitability/policy-context boundary without promoting runtime policy-pack support; Slice 3 declares `AdvisoryPolicyEvaluationRecord:v1` as a proposed, blocked data product with validating trust telemetry and no policy capability promotion; Slice 4 adds `rfc0025.policy-source-readiness.v1` to proposal evidence so missing source-owner evidence is explicit before policy evaluation exists, with evidence in `docs/rfcs/RFC-0025-slice-4-upstream-source-evidence-completion.md`; Slice 5 implements the `rfc0025.policy-pack-catalog.v1` catalog, schema validation, reference packs, hash-backed activation, maker-checker controls, and audit events, with evidence in `docs/rfcs/RFC-0025-slice-5-policy-pack-catalog-schema-activation.md`; Slice 6 implements the internal `rfc0025.policy-evaluation-engine.v1` applicability and rule-evaluation engine for active policy packs, with source-backed material rule results and no persistence/API/product-surface promotion, with evidence in `docs/rfcs/RFC-0025-slice-6-policy-applicability-and-evaluation-engine.md`; Slice 7 implements internal `rfc0025.policy-evaluation-persistence.v1` finalized records, source/policy/evaluation hashes, duplicate prevention, idempotent replay, append-only review/sign-off/report-archive events, and replay hash comparison, with evidence in `docs/rfcs/RFC-0025-slice-7-policy-evaluation-persistence-replay-audit.md`; Slice 8 implements certified Advise evaluation APIs, review queue projection, replay, lineage, append-only review/sign-off/report-reference events, and sign-off source packages, with evidence in `docs/rfcs/RFC-0025-slice-8-certified-apis-and-openapi.md`; Slice 9 implements Advise source workflow projection and sign-off decision recording over finalized policy records, including approval dependencies, disclosure and consent requirements, conflict posture, SLA aging, maker-checker enforcement, source-hash validation, and append-only sign-off events, with evidence in `docs/rfcs/RFC-0025-slice-9-policy-approval-consent-signoff-workflow.md`. Gateway/Workbench policy support, report/render/archive realization, active data-product promotion, and client-ready publication remain gated. | RFC-0010, RFC-0013, RFC-0015, RFC-0020, RFC-0021, RFC-0022, RFC-0024 | `docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md` |
| RFC-0026 | Advisor Cockpit Operating Workflow | DRAFT - GOLD-STANDARD IMPLEMENTATION PLAN | Active crown-jewel feature roadmap; RFC is the execution source and WTBD is closed historical context only | RFC-0004, RFC-0013, RFC-0017, RFC-0018, RFC-0019, RFC-0021, RFC-0022, RFC-0024, RFC-0025 | `docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md` |
| RFC-0027 | Governed Advisory AI Copilot | DRAFT - GOLD-STANDARD IMPLEMENTATION PLAN | Active crown-jewel feature roadmap; RFC is the execution source and WTBD is closed historical context only | RFC-0021, RFC-0022, RFC-0023, RFC-0024, RFC-0025, RFC-0026 | `docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md` |
| RFC-0028 | Bank Demo Journey and Client-Ready Proof | DRAFT - GOLD-STANDARD IMPLEMENTATION PLAN | Active crown-jewel feature roadmap; RFC is the execution source and WTBD is closed historical context only | RFC-0013, RFC-0019, RFC-0020, RFC-0021, RFC-0022, RFC-0023, RFC-0024, RFC-0025, RFC-0026, RFC-0027 | `docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md` |

## Implemented

Implemented RFCs:
- `RFC-0003`
- `RFC-0004`
- `RFC-0005`
- `RFC-0006`
- `RFC-0007`
- `RFC-0008`
- `RFC-0009`
- `RFC-0010`
- `RFC-0011`
- `RFC-0012`
- `RFC-0013`
- `RFC-0019`
- `RFC-0020`
- `RFC-0021`
- `RFC-0022`
- `RFC-0023` advisor-review narrative evidence
- `RFC-0024` advisor-use proposal memo evidence

## Not Yet Implemented

Open RFCs still relevant to the advisory roadmap:
- `RFC-0014`
- `RFC-0015`
- `RFC-0016`
- `RFC-0017`
- `RFC-0018`
- `RFC-0025`
- `RFC-0026`
- `RFC-0027`
- `RFC-0028`

Recommended near-term implementation order:
1. `RFC-0025` enterprise suitability and best-interest policy packs
2. `RFC-0026` advisor cockpit operating workflow
3. `RFC-0027` governed advisory AI copilot
4. `RFC-0028` bank demo journey and client-ready proof
5. `RFC-0014` remaining replay and data-quality backbone deltas not already covered by current implementation
6. `RFC-0016` costs, fees, and transaction frictions
7. `RFC-0017` remaining execution-boundary stabilization deltas not already covered by current implementation

Deferred but retained:
- `RFC-0002`

## Archived / Not Needed For Active Planning

| Item | Disposition | Reason | File |
| --- | --- | --- | --- |
| RFC-0001 | Superseded / historical | First production-profile cutover was valuable, but RFC-0005 is now the unified runtime and persistence direction. | `docs/rfcs/RFC-0001-postgres-only-production-mode-cutover.md` |
| Raw advisory drafts | Archived / not needed for active planning | Historical duplicates retained for traceability only. They are not the source of truth for current advisory planning. | `docs/rfcs/archive/raw-advisory-drafts/` |

Current note:
- `RFC-0005` now owns runtime persistence direction.
- `RFC-0013` now owns lifecycle and audit model direction.
- RFC-0023 Slice 0 source-map evidence lives in
  `docs/rfcs/RFC-0023-slice-0-critical-review-source-map-and-product-gap-allocation.md`; it is a
  scope and source-authority gate, not a supported proposal narrative capability.
- RFC-0023 Slice 1 platform-scaffolding evidence lives in
  `docs/rfcs/RFC-0023-slice-1-platform-automation-and-scaffolding-review.md`; it records a
  deliberate no-platform-change decision and the platform/repo-native controls later slices must
  reuse.
- RFC-0023 Slice 2 cleanup and structure evidence lives in
  `docs/rfcs/RFC-0023-slice-2-cleanup-and-structure.md`; it records the workspace-rationale
  evidence boundary cleanup and the removal of premature client-ready simulation wording without
  promoting generated proposal narrative.
- RFC-0023 Slice 3 current-state assessment and narrative contract evidence lives in
  `docs/rfcs/RFC-0023-slice-3-current-state-assessment-and-narrative-contract-baseline.md`; it
  defines the additive `proposal_narrative` contract baseline and proves no public API v2 is needed
  before implementation-bearing slices.
- RFC-0023 Slice 4 data-product and supportability evidence lives in
  `docs/rfcs/RFC-0023-slice-4-data-product-and-supportability-baseline.md`; it records the
  non-promotion decision for narrative data-product, trust-telemetry, and `/platform/capabilities`
  posture until deterministic advisor-review narrative readiness exists.
- RFC-0023 Slice 5 grounding-packet and deterministic-template evidence lives in
  `docs/rfcs/RFC-0023-slice-5-grounding-packet-and-deterministic-template-baseline.md`; it adds
  opt-in deterministic `ADVISOR_REVIEW` narrative in the proposal artifact path without AI
  dependency, while standalone endpoints, persistence, review approval, replay, AI-assisted, and
  client-ready states remain gated.
- RFC-0023 Slice 6 narrative-policy, disclosure, and guardrail evidence lives in
  `docs/rfcs/RFC-0023-slice-6-narrative-policy-disclosure-and-guardrail-framework.md`; it adds
  deterministic policy metadata, approved disclosure selection, unsupported-claim guardrails, and
  client-ready policy blockers to the artifact-path narrative response while standalone endpoints,
  persistence, review approval, replay, AI-assisted, and client-ready states remain gated.
- RFC-0023 Slice 7 lotus-ai adapter and AI-assisted draft evidence lives in
  `docs/rfcs/RFC-0023-slice-7-lotus-ai-adapter-and-ai-assisted-draft-baseline.md`; it adds
  opt-in `AI_ASSISTED_DRAFT` advisor-review narrative in the proposal artifact path through a
  narrow workflow-pack adapter with deterministic fallback and guardrail validation while
  standalone endpoints, persistence, review approval, replay, compliance-review, client-draft,
  client-ready, data-product, and `/platform/capabilities` states remain gated.
- RFC-0023 Slice 8 review workflow, persistence, idempotency, artifact, and replay evidence lives
  in `docs/rfcs/RFC-0023-slice-8-review-workflow-persistence-idempotency-artifact-and-replay.md`;
  it adds version-scoped `NARRATIVE_REVIEWED` events, review idempotency, source narrative hashes,
  and exact replay evidence for proposal-version narratives while compliance-review, client-draft,
  client-ready, report/render/archive, Gateway, Workbench, data-product, trust-telemetry, and
  `/platform/capabilities` promotion remain gated.
- RFC-0023 Slice 9 alternatives, decision summary, and policy evidence integration evidence lives
  in
  `docs/rfcs/RFC-0023-slice-9-alternatives-decision-summary-and-policy-evidence-integration.md`;
  it enriches deterministic advisor-review sections with persisted RFC-0021 decision-summary,
  RFC-0022 alternatives tradeoff, approval/remediation, material-change, and limitation evidence
  while compliance-review, client-draft, client-ready, report/render/archive, Gateway, Workbench,
  data-product, trust-telemetry, and `/platform/capabilities` promotion remain gated.
- RFC-0023 Slice 10 certified API and OpenAPI evidence lives in
  `docs/rfcs/RFC-0023-slice-10-certified-api-and-openapi.md`; it certifies the existing additive
  advisor-review narrative API shape, canonical proposal-version review route, proposal/async
  replay evidence routes, response documentation, idempotency header guidance, stale-route absence,
  and material returned-field coverage. Standalone narrative read/regeneration is tracked
  separately in Slice 10B.
- RFC-0023 Slice 10B standalone narrative read/regeneration API evidence lives in
  `docs/rfcs/RFC-0023-slice-10B-standalone-narrative-read-regeneration-api.md`; it adds
  read-only exact persisted narrative retrieval and non-persistent advisor-review regeneration
  candidates under the canonical proposal-version route family while compliance-review,
  client-draft, client-ready, data-product, trust-telemetry, canonical demo screenshot proof, and
  `/platform/capabilities` promotion remain gated.
- RFC-0023 Slice 11A reviewed narrative report-request package propagation evidence lives in
  `docs/rfcs/RFC-0023-slice-11A-reviewed-narrative-report-request-package-propagation.md`; it
  adds `include_reviewed_narrative` support for report requests, requires approved narrative review
  and matching source hash, propagates a compact package to the report seam, and persists delivery
  evidence while downstream artifact realization remains gated outside `lotus-advise`.
- RFC-0023 Slice 11B/11C report and render realization evidence lives in
  `docs/rfcs/RFC-0023-slice-11B-11C-report-render-reviewed-narrative-realization.md`; it records
  that `lotus-report` now consumes and snapshots the reviewed advisory narrative package and
  `lotus-render` now renders the optional portfolio-review advisory narrative page; archive
  closure is tracked separately in Slice 11D and Gateway/Workbench posture is tracked separately in
  Slice 11E, while client-ready, data-product, trust-telemetry, and `/platform/capabilities`
  promotion remain gated.
- RFC-0023 Slice 11D archive artifact realization evidence lives in
  `docs/rfcs/RFC-0023-slice-11D-archive-reviewed-narrative-artifact-realization.md`; it records
  that `lotus-archive` now stores a support-safe reviewed advisory narrative summary for rendered
  advisor-use portfolio-review artifacts while Gateway/Workbench posture is tracked separately in
  Slice 11E and client-ready, data-product, trust-telemetry, and `/platform/capabilities`
  promotion remain gated.
- RFC-0023 Slice 11E Gateway/Workbench realization evidence lives in
  `docs/rfcs/RFC-0023-slice-11E-gateway-workbench-reviewed-narrative-realization.md`; it records
  that `lotus-gateway` now exposes product-facing reviewed-narrative posture from canonical
  `lotus-advise` APIs and `lotus-workbench` renders the Gateway-backed advisor-use proposal
  narrative posture while compliance-review, client-draft, client-ready, data-product,
  trust-telemetry, canonical demo screenshot proof, and `/platform/capabilities` promotion remain
  gated.
- RFC-0023 Slice 11F narrative data-product, trust-telemetry, and capability promotion evidence
  lives in
  `docs/rfcs/RFC-0023-slice-11F-narrative-data-product-trust-capability-promotion.md`; it promotes
  advisor-review proposal narrative evidence as `ProposalNarrativeEvidence:v1`, adds repo-native
  trust telemetry, refreshes platform catalog/certification artifacts, and publishes the bounded
  `advisory.proposals.reviewed_narrative_evidence` feature plus
  `advisory_proposal_reviewed_narrative_evidence` workflow in `/platform/capabilities` while
  compliance-review, client-draft, client-ready publication, and canonical demo screenshot proof
  remained gated before Slice 12.
- RFC-0023 Slice 12 live/canonical proof closure evidence lives in
  `docs/rfcs/RFC-0023-slice-12-live-validation-canonical-proof-and-operator-evidence.md`; it
  closes stateful live narrative proof, deterministic guardrail-failure reproduction, optional
  AI-assisted validation where enabled, and governed Workbench `proposal.narrative_posture`
  screenshot proof for advisor-review posture. Compliance-review, client-draft, client-ready
  publication, and external client communication remain gated future scope rather than supported
  RFC-0023 closure claims.
- RFC-0023 Slice 13/14 closure-hardening review evidence lives in
  `docs/rfcs/RFC-0023-slice-13-14-closure-hardening-and-review.md`; it records the gold-standard
  review finding that RFC-0023 is not a full client-ready publication capability and hardens the
  review workflow so an otherwise clean advisor-review narrative still cannot return
  `APPROVED_FOR_CLIENT_READY`.
- RFC-0024 Slice 0 source-map evidence lives in
  `docs/rfcs/RFC-0024-slice-0-critical-review-source-map-and-product-gap-allocation.md`; it is a
  critical-review, source-authority, cross-repo ownership, and product-gap allocation gate. It does
  not implement advisor proposal memo generation, memo APIs, memo persistence, report packages,
  Gateway/Workbench memo surfaces, data-product promotion, or client-ready memo publication.
- RFC-0024 Slice 1 platform-scaffolding evidence lives in
  `docs/rfcs/RFC-0024-slice-1-platform-automation-and-scaffolding-review.md`; it records a
  deliberate no-platform-change decision before memo domain work, rejects one-off local scaffolding,
  and pins the platform/repo-native controls later memo slices must reuse.
- RFC-0024 Slice 2 cleanup and structure evidence lives in
  `docs/rfcs/RFC-0024-slice-2-cleanup-and-structure.md`; it moves reviewed narrative report-package
  business rules from the API service layer into `src/core/proposals/report_narrative_package.py`
  and adds engine-level tests before memo domain work begins.
- RFC-0024 Slice 3 data-product and platform-hardening evidence lives in
  `docs/rfcs/RFC-0024-slice-3-data-product-and-platform-hardening.md`; it declares proposed/blocked
  `AdvisoryProposalMemoEvidencePack:v1` producer and trust-telemetry posture while keeping memo
  routes, capabilities, active mesh policy, and client-ready support unpromoted.
- RFC-0024 Slice 4 upstream source evidence completion lives in
  `docs/rfcs/RFC-0024-slice-4-upstream-source-evidence-completion.md`; it adds a persisted
  `rfc0024.memo-source-readiness.v1` manifest to proposal evidence bundles and keeps missing
  source-owner facts explicit instead of inventing memo claims.
- RFC-0024 Slice 5 memo domain model and pure builder evidence lives in
  `docs/rfcs/RFC-0024-slice-5-memo-domain-model-and-pure-builder.md`; it adds
  `AdvisoryProposalMemoEvidencePack` models and deterministic pure builder behavior while keeping
  memo APIs, memo persistence, report/render/archive support, Gateway/Workbench support, active
  data-product support, and client-ready memo claims planned.
- RFC-0024 Slice 6 persistence, replay, idempotency, and audit evidence lives in
  `docs/rfcs/RFC-0024-slice-6-persistence-replay-idempotency-and-audit.md`; it adds durable memo
  records, memo idempotency, replay metadata, and memo audit events while keeping memo APIs,
  report/render/archive support, Gateway/Workbench support, active data-product support, and
  client-ready memo claims planned.
- RFC-0024 Slice 7 certified APIs and OpenAPI evidence lives in
  `docs/rfcs/RFC-0024-slice-7-certified-apis-and-openapi.md`; it exposes canonical
  `lotus-advise` memo create/read/projection/review/report-package-event/lineage/replay endpoints
  under the `Advisory Proposal Memo` OpenAPI tag while keeping Gateway/Workbench product support,
  report/render/archive realization, active data-product support, and client-ready memo claims
  planned.
- RFC-0024 Slice 8 policy, fees, costs, conflicts, and disclosures evidence lives in
  `docs/rfcs/RFC-0024-slice-8-policy-fees-costs-conflicts-and-disclosures.md`; it enriches
  memo-critical suitability, product eligibility, cost/fee/tax/friction limitation, disclosure, and
  conflict blocker sections while keeping full policy packs, report/render/archive realization,
  Gateway/Workbench product support, active data-product support, and client-ready memo claims
  planned.
- RFC-0024 Slice 9 report, render, and archive realization evidence lives in
  `docs/rfcs/RFC-0024-slice-9-report-render-archive-realization.md`; it sends advisor-reviewed
  memo packages through `lotus-report`, `lotus-render`, and `lotus-archive` while keeping Gateway,
  Workbench, active data-product support, AI commentary, and client-ready memo claims planned.
- RFC-0024 Slice 10 AI narrative and review-gated commentary evidence lives in
  `docs/rfcs/RFC-0024-slice-10-ai-narrative-and-review-gated-commentary.md`; it adds the bounded
  `proposal_memo_commentary.pack@v1` workflow-pack path, append-only AI lineage, review-required
  commentary posture, and deterministic AI-unavailable behavior while keeping Gateway, Workbench,
  active data-product support, commercial/demo claims, and client-ready memo claims planned.
- RFC-0024 Slice 11 Gateway and Workbench product-realization evidence lives in
  `docs/rfcs/RFC-0024-slice-11-gateway-workbench-product-realization.md`; it routes Gateway
  proposal memo APIs through canonical Advise endpoints and adds Workbench Gateway/BFF-only memo
  posture, projection, report-package, archive-ref, AI-commentary, lineage, replay, degraded, and
  blocked-state proof while keeping active data-product support, commercial/demo claims, and
  client-ready memo claims unpromoted.
- RFC-0024 Slice 12 commercial, demo, and RFP-support evidence lives in
  `docs/rfcs/RFC-0024-slice-12-commercial-demo-rfp-support.md`. Memo-specific claim-controlled
  product material lives in `docs/commercial/RFC-0024-advisor-proposal-memo-commercial-support.md`
  and covers one-pager wording, demo notes, API examples, architecture flow, operator guidance, and
  RFP-safe wording while keeping active data-product support, full RFC-0028 bank-demo/RFP package
  claims, and client-ready memo claims unpromoted.
- RFC-0024 Slice 13 implementation-proof evidence lives in
  `docs/rfcs/RFC-0024-slice-13-implementation-proof.md`; it adds a `proposal_memo` live-suite
  snapshot covering Advise memo APIs, the stateful source dependency path, advisor projection,
  advisor-use report/render/archive request posture, review-gated AI commentary, lineage, replay
  hashes, degraded report posture, and stale-hash/client-ready blocked paths.
- RFC-0024 Slice 14 data-product promotion and supportability-hardening evidence lives in
  `docs/rfcs/RFC-0024-slice-14-data-product-promotion-and-supportability-hardening.md`; it promotes
  `AdvisoryProposalMemoEvidencePack:v1` as an active advisor-use data product with current trust
  telemetry, `/platform/capabilities`, and platform SLO/access/evidence-policy posture while keeping
  full RFC-0028 bank-demo/RFP package claims and client-ready memo claims unpromoted.
- RFC-0024 Slice 15 final hardening and review evidence lives in
  `docs/rfcs/RFC-0024-slice-15-final-hardening-and-review.md`; canonical `PB_SG_GLOBAL_BAL_001`
  Workbench validation proves the advisor journey and `proposal.memo_evidence_pack` panel are ready
  and Gateway-backed while client-ready memo publication remains gated.
- RFC-0024 Slice 16 final closure evidence lives in
  `docs/rfcs/RFC-0024-slice-16-final-closure.md`; README, wiki source, supported-features, RFC
  status, repo context, domain-product declaration, trust telemetry, and proof summaries carry
  closure truth, wiki publication was completed after merge, and no Lotus context or skill guidance
  change was required.
- RFC-0024 Slice 17 post-completion communication evidence lives in
  `docs/rfcs/RFC-0024-slice-17-post-completion-communication.md`; `lotus-platform` PR #357 added
  the employer-safe LinkedIn draft and content-ledger entry without client-ready memo publication,
  external client communication, or full RFC-0028 bank-demo/RFP claims.
- RFC-0025 Slice 1 platform-scaffolding evidence lives in
  `docs/rfcs/RFC-0025-slice-1-platform-automation-and-scaffolding-review.md`; it records that
  existing platform and repo-native controls are sufficient before policy domain work, rejects
  policy-pack-only local scaffolding, and keeps policy-pack catalog APIs, policy activation,
  policy evaluation, policy persistence, review queues, report/render/archive sign-off packs,
  Gateway/Workbench policy surfaces, data-product promotion, and client-ready publication
  unimplemented.
- RFC-0025 Slice 2 cleanup and structure evidence lives in
  `docs/rfcs/RFC-0025-slice-2-cleanup-and-structure-review.md`; it centralizes current
  advisory-policy context status interpretation, removes duplicate suitability scanner baseline
  wiring, and keeps runtime policy-pack capability unimplemented and unpromoted.
- RFC-0025 Slice 9 policy workflow evidence lives in
  `docs/rfcs/RFC-0025-slice-9-policy-approval-consent-signoff-workflow.md`; it adds Advise
  source workflow projection and sign-off decisions over finalized policy records while keeping
  Gateway/Workbench policy support, report/render/archive realization, active data-product
  promotion, and client-ready publication gated.

Implementation evidence:
- `docs/rfcs/RFC-0024-slice-0-critical-review-source-map-and-product-gap-allocation.md`
- `docs/rfcs/RFC-0024-slice-1-platform-automation-and-scaffolding-review.md`
- `docs/rfcs/RFC-0024-slice-2-cleanup-and-structure.md`
- `docs/rfcs/RFC-0024-slice-3-data-product-and-platform-hardening.md`
- `docs/rfcs/RFC-0024-slice-4-upstream-source-evidence-completion.md`
- `docs/rfcs/RFC-0024-slice-5-memo-domain-model-and-pure-builder.md`
- `docs/rfcs/RFC-0024-slice-6-persistence-replay-idempotency-and-audit.md`
- `docs/rfcs/RFC-0024-slice-7-certified-apis-and-openapi.md`
- `docs/rfcs/RFC-0024-slice-8-policy-fees-costs-conflicts-and-disclosures.md`
- `docs/rfcs/RFC-0024-slice-9-report-render-archive-realization.md`
- `docs/rfcs/RFC-0024-slice-10-ai-narrative-and-review-gated-commentary.md`
- `docs/rfcs/RFC-0024-slice-11-gateway-workbench-product-realization.md`
- `docs/rfcs/RFC-0024-slice-12-commercial-demo-rfp-support.md`
- `docs/rfcs/RFC-0024-slice-13-implementation-proof.md`
- `docs/rfcs/RFC-0024-slice-14-data-product-promotion-and-supportability-hardening.md`
- `docs/rfcs/RFC-0024-slice-15-final-hardening-and-review.md`
- `docs/rfcs/RFC-0024-slice-16-final-closure.md`
- `docs/rfcs/RFC-0024-slice-17-post-completion-communication.md`
- `docs/commercial/RFC-0024-advisor-proposal-memo-commercial-support.md`
- `docs/rfcs/RFC-0025-slice-1-platform-automation-and-scaffolding-review.md`
- `docs/rfcs/RFC-0025-slice-2-cleanup-and-structure-review.md`
- `docs/rfcs/RFC-0025-slice-7-policy-evaluation-persistence-replay-audit.md`
- `docs/rfcs/RFC-0025-slice-8-certified-apis-and-openapi.md`
- `docs/rfcs/RFC-0025-slice-9-policy-approval-consent-signoff-workflow.md`
