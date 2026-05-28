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
| RFC-0025 | Enterprise Suitability and Best-Interest Policy Packs | IMPLEMENTED for advisor/compliance policy evidence; client-ready authority remains gated | RFC is implemented through Slice 17 for versioned policy packs, source readiness, catalog/activation, source-backed evaluation, persistence/replay, certified APIs, workflow/sign-off posture, report-package handoff, bounded AI evidence, Gateway/Workbench product realization, commercial support material, live-suite `proposal_policy` proof, centralized supportability hardening, active `AdvisoryPolicyEvaluationRecord:v1` data-product posture, current trust telemetry, `/platform/capabilities`, platform SLO/access/evidence-policy support, and post-completion communication. The 2026-05-27 gold-pass hardening requires portfolio identity on policy evaluation records and proves the review queue is portfolio-scoped through Advise, Gateway, Workbench, and canonical live validation for `PB_SG_GLOBAL_BAL_001`. Evidence lives in Slice 0-17 records including `docs/rfcs/RFC-0025-slice-16-final-closure.md` and `docs/rfcs/RFC-0025-slice-17-post-completion-communication.md`. Completed approval/waiver authority, completed sign-off authority, client-ready publication, external client communication, and full RFC-0028 bank-demo/RFP package claims remain gated. | RFC-0010, RFC-0013, RFC-0015, RFC-0020, RFC-0021, RFC-0022, RFC-0024 | `docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md` |
| RFC-0026 | Advisor Cockpit Operating Workflow | IMPLEMENTED for source-owned first-wave advisor cockpit operating workflow | Active crown-jewel feature source of truth. Advise action/snapshot/supportability/acknowledgement APIs, Gateway publication, Workbench cockpit surface, canonical `PB_SG_GLOBAL_BAL_001` proof, active cockpit data products, trust telemetry, and `/platform/capabilities` promotion are implemented for the first-wave source-owned cockpit scope. Slice 16 hardens live canonical proof for action detail, pagination, role projection, invalid-cursor rejection, preparation packets, house-view impact, supportability posture, source lineage, and lowest-useful-layer regression tests for live defects. | RFC-0004, RFC-0013, RFC-0017, RFC-0018, RFC-0019, RFC-0021, RFC-0022, RFC-0024, RFC-0025 | `docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md` |
| RFC-0027 | Governed Advisory AI Copilot | DRAFT - GOLD-STANDARD IMPLEMENTATION PLAN - SLICE 0 READY | Active crown-jewel feature roadmap; RFC is the execution source and WTBD is closed historical context only. Slice 0 resolves first-wave action families, selected API direction, source-authority decisions, canonical `RFC27_ADVISORY_COPILOT_CANONICAL` proof expectations, seed/automation scope, and no-day-2/no-wave-2 closure posture before implementation begins. | RFC-0021, RFC-0022, RFC-0023, RFC-0024, RFC-0025, RFC-0026 | `docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md` |
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
- `RFC-0025` advisor/compliance policy evidence
- `RFC-0026` source-owned first-wave advisor cockpit operating workflow

## Not Yet Implemented

Open RFCs still relevant to the advisory roadmap:
- `RFC-0014`
- `RFC-0015`
- `RFC-0016`
- `RFC-0017`
- `RFC-0018`
- `RFC-0027`
- `RFC-0028`

Recommended near-term implementation order:
1. `RFC-0027` governed advisory AI copilot
2. `RFC-0028` bank demo journey and client-ready proof
3. `RFC-0014` remaining replay and data-quality backbone deltas not already covered by current implementation
4. `RFC-0016` costs, fees, and transaction frictions
5. `RFC-0017` remaining execution-boundary stabilization deltas not already covered by current implementation

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
  report/render/archive realization, Gateway/Workbench policy support, active data-product
  promotion, and client-ready publication gated.
- RFC-0025 Slice 10 policy report-package evidence lives in
  `docs/rfcs/RFC-0025-slice-10-report-render-archive-realization.md`; it adds Advise-owned typed
  lotus-report handoff for signed-off policy evaluations, records report/render/archive refs in
  policy lineage, and keeps client-ready document generation blocked.
- RFC-0025 Slice 11 AI policy-evidence evidence lives in
  `docs/rfcs/RFC-0025-slice-11-ai-policy-evidence-boundary.md`; it adds redacted bounded
  `lotus-ai` policy evidence handoff, forbidden-action rejection, deterministic unavailable
  posture, prompt/output lineage, human review, and non-authoritative client-ready blocked posture.
- RFC-0025 Slice 12 Gateway and Workbench product-realization evidence lives in
  `docs/rfcs/RFC-0025-slice-12-gateway-workbench-product-realization.md`; it records the merged
  Gateway BFF policy surface and Workbench Gateway-only Suitability Review surface while keeping
  active data-product promotion, live proof, approval/waiver authority, completed sign-off
  authority, and client-ready publication gated.
- RFC-0025 Slice 13 commercial, demo, and RFP-support evidence lives in
  `docs/rfcs/RFC-0025-slice-13-commercial-demo-rfp-support.md`. Policy-pack-specific
  claim-controlled product material lives in
  `docs/commercial/RFC-0025-enterprise-policy-pack-commercial-support.md` and covers one-pager
  wording, demo notes, API examples, architecture flow, operator guidance, security posture, and
  RFP-safe wording while keeping active data-product promotion, live proof, approval/waiver
  authority, completed sign-off authority, and client-ready publication gated.
- RFC-0025 Slice 14 implementation-proof evidence lives in
  `docs/rfcs/RFC-0025-slice-14-implementation-proof.md`; it adds a `proposal_policy` live-suite
  snapshot covering Advise policy evaluation create/read/review-queue/workflow/sign-off-package/
  sign-off-decision/report-package/AI-evidence/lineage/replay endpoints, SG reference-pack
  policy hashes, source refs and gaps, requirement counts, workflow and sign-off posture,
  report/render/archive refs or degraded reason, bounded AI posture, replay hash comparison, and
  stale-hash/client-ready/forbidden-AI blocked paths while keeping active data-product promotion,
  completed approval/waiver authority, completed sign-off authority, and client-ready publication
  gated.
- RFC-0025 Slice 15 final-hardening evidence lives in
  `docs/rfcs/RFC-0025-slice-15-final-hardening-and-review.md`; it centralizes policy-pack
  supportability truth, removes duplicated stale supportability maps, updates OpenAPI/schema
  examples, and proves Gateway/Workbench product support plus signed-off report-package handoff are
  represented accurately while active data-product promotion, completed approval/waiver authority,
  completed sign-off authority, and client-ready publication remain gated.
- RFC-0025 Slice 16 final-closure evidence lives in
  `docs/rfcs/RFC-0025-slice-16-final-closure.md`; it promotes
  `AdvisoryPolicyEvaluationRecord:v1` as an active advisor/compliance policy evidence product with
  current trust telemetry, `/platform/capabilities`, and platform SLO/access/evidence-policy
  posture while completed approval/waiver authority, completed sign-off authority, client-ready
  publication, external communication, and full RFC-0028 bank-demo/RFP claims remain gated.
- RFC-0025 Slice 17 post-completion communication evidence lives in
  `docs/rfcs/RFC-0025-slice-17-post-completion-communication.md`; the
  `lotus-platform` LinkedIn draft
  `LI-2026-05-26-042-policy-evidence-should-show-its-limits.md` and content-ledger entry are
  employer-safe, non-promotional, and do not claim completed approval/waiver authority, completed
  sign-off authority, client-ready publication, external client communication, bank adoption, or
  full RFC-0028 bank-demo/RFP support.
- RFC-0026 Slice 1 platform-scaffolding evidence lives in
  `docs/rfcs/RFC-0026-slice-1-platform-automation-and-scaffolding-review.md`; it records that
  existing platform and repo-native controls are sufficient before cockpit domain work, rejects
  premature local/platform cockpit scaffolds, and keeps canonical `RFC26_ADVISOR_COCKPIT_CANONICAL`
  seed and Workbench automation as mandatory subsequent RFC-0026 work once backend, Gateway, and
  Workbench behavior exists.
- RFC-0026 Slice 2 cleanup and structure evidence lives in
  `docs/rfcs/RFC-0026-slice-2-cleanup-and-structure.md`; it creates the dedicated
  `src/core/advisor_cockpit/` package with typed cockpit models, vocabulary, stable action sorting,
  and pagination defaults while keeping APIs, persistence, data products, Gateway, Workbench,
  canonical seed data, and supported advisor-cockpit claims unpromoted until subsequent RFC-0026
  slices implement and prove them.
- RFC-0026 Slice 3 data-product evidence lives in
  `docs/rfcs/RFC-0026-slice-3-data-product-and-platform-hardening.md`; it records a non-promoting
  posture for `AdvisorCockpitOperatingSnapshot:v1` and `AdvisoryActionItemRegister:v1`, adds tests
  that block premature declarations, trust telemetry, and `/platform/capabilities` promotion, and
  keeps data-product promotion mandatory inside RFC-0026 once runtime, Gateway, Workbench, mesh,
  and canonical proof exist.
- RFC-0026 Slice 4 cockpit domain evidence lives in
  `docs/rfcs/RFC-0026-slice-4-cockpit-domain-model-and-vocabulary.md`; it adds the pure core
  `src/core/advisor_cockpit/action_factory.py` source-backed action construction layer, covers
  policy-review, memo-blocked, meeting-preparation, supportability, and unsupported-capability
  actions with behavior tests, and keeps APIs, persistence, data products, Gateway, Workbench, and
  canonical proof unpromoted until mandatory subsequent RFC-0026 slices implement them.
- RFC-0026 Slice 5 source-read-model evidence lives in
  `docs/rfcs/RFC-0026-slice-5-source-read-model-and-aggregation.md`; it adds
  `src/core/advisor_cockpit/source_read_model.py` for preloaded source aggregation across
  proposals, policy evaluations, memos, supportability events, and unsupported capabilities,
  preserving lineage and avoiding repository-loop behavior before runtime API wiring.
- RFC-0026 Slice 6 priority/SLA evidence lives in
  `docs/rfcs/RFC-0026-slice-6-priority-sla-acknowledgement-rules.md`; it adds
  `src/core/advisor_cockpit/rules.py` for deterministic SLA age bands, owner-blocking status
  checks, and acknowledgement posture that cannot clear blocking action ownership.
- RFC-0026 Slice 7 Advise API evidence lives in
  `docs/rfcs/RFC-0026-slice-7-certified-advise-apis.md`; it adds Advise-owned cockpit action,
  snapshot, supportability, and idempotent acknowledgement APIs, with persistent acknowledgement
  storage and OpenAPI boundary tests, while keeping Gateway, Workbench, data products, and
  canonical proof unpromoted until mandatory subsequent RFC-0026 slices.
- RFC-0026 Slice 8 preparation and follow-up evidence lives in
  `docs/rfcs/RFC-0026-slice-8-meeting-preparation-client-follow-up.md`; it adds the paginated
  Advise preparation-packet API and source-backed client follow-up actions while keeping CRM,
  calendar scheduling, external client communication, and client-ready publication blocked.
- RFC-0026 Slice 9 supervisory queue evidence lives in
  `docs/rfcs/RFC-0026-slice-9-supervisory-approval-compliance-queues.md`; it adds source-backed
  risk, compliance, and consent queue projection with batched approval reads, deterministic owner
  roles, and blocked completed-approval/client-ready authority.
- RFC-0026 Slice 10 readiness evidence lives in
  `docs/rfcs/RFC-0026-slice-10-readiness-execution-house-view.md`; it adds report/archive
  readiness, execution handoff/status attention, and explicit source-batched tactical house-view
  impact actions while preserving report/archive, OMS, and DPM source-of-record boundaries.
- RFC-0026 Slice 13 data-product and capability-promotion evidence lives in
  `docs/rfcs/RFC-0026-slice-13-data-product-capability-promotion.md`; it promotes
  `AdvisorCockpitOperatingSnapshot:v1`, `AdvisoryActionItemRegister:v1`, trust telemetry,
  `/platform/capabilities`, and Advise supportability after Gateway, Workbench, and canonical
  `PB_SG_GLOBAL_BAL_001` proof.
- RFC-0026 Slice 16 implementation-proof evidence lives in
  `docs/rfcs/RFC-0026-slice-16-implementation-proof.md`; it records hardened live canonical proof
  for action detail, cursor pagination, invalid-cursor rejection, compliance and DPM role
  projection, preparation packets, house-view impact, acknowledgement idempotency, supportability
  posture, and action evidence/lineage. The slice also records live defects fixed at the owning
  layer and pinned by lower-level tests before rerun.
- RFC-0027 Slice 1 platform-scaffolding evidence lives in
  `docs/rfcs/RFC-0027-slice-1-platform-automation-and-scaffolding-review.md`; it records that
  existing platform and repo-native controls are sufficient before copilot domain work, rejects
  premature local/platform copilot scaffolds, and keeps `RFC27_ADVISORY_COPILOT_CANONICAL` seed and
  Workbench automation as mandatory RFC-0027 Slice 12 work once backend, Gateway, and Workbench
  behavior exists.
- RFC-0027 Slice 2 cleanup and structure evidence lives in
  `docs/rfcs/RFC-0027-slice-2-cleanup-and-structure.md`; it creates
  `src/core/advisory_copilot/` with the first-wave action catalog, source/evidence vocabulary,
  guardrail reason-code foundation, review posture mapping, workflow-pack boundary metadata, and
  business-facing projection labels while keeping APIs, persistence, `lotus-ai` invocation,
  Gateway, Workbench, data-product promotion, canonical seed, and supported copilot claims
  unpromoted until subsequent RFC-0027 slices implement and prove them.
- RFC-0027 Slice 3 data-product evidence lives in
  `docs/rfcs/RFC-0027-slice-3-data-product-and-platform-hardening.md`; it records a non-promoting
  posture for `AdvisoryCopilotInteractionRecord:v1`, `AdvisoryCopilotEvidencePacket:v1`, and
  `AdvisoryCopilotReviewRecord:v1`, adds tests that block premature declarations, trust telemetry,
  and `/platform/capabilities` promotion, and keeps data-product promotion mandatory inside
  RFC-0027 once runtime, Gateway, Workbench, mesh, and canonical proof exist.
- RFC-0027 Slice 4 domain-model evidence lives in
  `docs/rfcs/RFC-0027-slice-4-domain-model-vocabulary-review-state.md`; it adds typed evidence
  packet, section, source-ref, lineage-ref, unsupported-evidence, retention-class, and review-state
  vocabulary while preserving blocked client-ready posture and no runtime/API promotion.
- RFC-0027 Slice 5 evidence-packet projection evidence lives in
  `docs/rfcs/RFC-0027-slice-5-evidence-packet-redaction-projection.md`; it adds a pure deterministic
  evidence-packet builder with audience projection, explicit missing/restricted unsupported posture,
  source refs, lineage refs, stable packet hashes, technical-copy leakage rejection, and blocked
  client-ready posture without source reads, persistence, APIs, `lotus-ai`, Gateway, Workbench, or
  support promotion.
- RFC-0027 Slice 6 guardrail evidence lives in
  `docs/rfcs/RFC-0027-slice-6-guardrail-unsupported-evidence-engine.md`; it adds pure guardrail
  evaluation for forbidden intents, missing source refs, prompt injection, client-ready wording,
  and sensitive technical leakage while keeping persistence, APIs, `lotus-ai`, Gateway, Workbench,
  canonical proof, and supported claims unpromoted.
- RFC-0027 Slice 7 workflow-pack evidence lives in
  `docs/rfcs/RFC-0027-slice-7-lotus-ai-workflow-pack-model-risk-controls.md`; it registers and
  consumes the six review-gated `lotus-ai` advisory copilot workflow packs, carries model-risk
  lineage, fails closed for unavailable or unsafe AI posture, and still keeps Advise copilot APIs,
  Gateway, Workbench, canonical proof, data products, and supported product claims unpromoted.
- RFC-0027 Slice 8 persistence evidence lives in
  `docs/rfcs/RFC-0027-slice-8-copilot-run-review-audit-retention.md`; it adds durable run,
  idempotency, review, audit, retention, legal-hold, and Postgres migration support while rejecting
  raw prompt/provider/unsafe-output storage and keeping API, Gateway, Workbench, canonical proof,
  data-product promotion, and supported product claims unpromoted.
- RFC-0027 Slice 9 certified API evidence lives in
  `docs/rfcs/RFC-0027-slice-9-certified-advise-apis-openapi.md`; it exposes Advise-owned copilot
  evidence-packet, Workbench-safe proposal-version source projection, action, run retrieval,
  review, supportability, and proposal-version run lookup APIs with OpenAPI coverage while keeping
  Workbench, canonical proof, data-product promotion, and supported product claims unpromoted.

RFC-0025 implementation evidence includes:

- `docs/rfcs/RFC-0025-slice-4-upstream-source-evidence-completion.md`
- `docs/rfcs/RFC-0025-slice-5-policy-pack-catalog-schema-activation.md`
- `docs/rfcs/RFC-0025-slice-6-policy-applicability-and-evaluation-engine.md`

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
- `docs/rfcs/RFC-0025-slice-10-report-render-archive-realization.md`
- `docs/rfcs/RFC-0025-slice-11-ai-policy-evidence-boundary.md`
- `docs/rfcs/RFC-0025-slice-12-gateway-workbench-product-realization.md`
- `docs/rfcs/RFC-0025-slice-13-commercial-demo-rfp-support.md`
- `docs/commercial/RFC-0025-enterprise-policy-pack-commercial-support.md`
- `docs/rfcs/RFC-0025-slice-14-implementation-proof.md`
- `docs/rfcs/RFC-0025-slice-15-final-hardening-and-review.md`
- `docs/rfcs/RFC-0025-slice-16-final-closure.md`
- `docs/rfcs/RFC-0026-slice-1-platform-automation-and-scaffolding-review.md`
- `docs/rfcs/RFC-0026-slice-2-cleanup-and-structure.md`
- `docs/rfcs/RFC-0026-slice-3-data-product-and-platform-hardening.md`
- `docs/rfcs/RFC-0026-slice-4-cockpit-domain-model-and-vocabulary.md`
- `docs/rfcs/RFC-0026-slice-5-source-read-model-and-aggregation.md`
- `docs/rfcs/RFC-0026-slice-6-priority-sla-acknowledgement-rules.md`
- `docs/rfcs/RFC-0026-slice-7-certified-advise-apis.md`
- `docs/rfcs/RFC-0026-slice-8-meeting-preparation-client-follow-up.md`
- `docs/rfcs/RFC-0026-slice-9-supervisory-approval-compliance-queues.md`
- `docs/rfcs/RFC-0026-slice-10-readiness-execution-house-view.md`
- `docs/rfcs/RFC-0026-slice-13-data-product-capability-promotion.md`
- `docs/rfcs/RFC-0026-slice-16-implementation-proof.md`
- `docs/rfcs/RFC-0027-slice-1-platform-automation-and-scaffolding-review.md`
- `docs/rfcs/RFC-0027-slice-2-cleanup-and-structure.md`
- `docs/rfcs/RFC-0027-slice-3-data-product-and-platform-hardening.md`
- `docs/rfcs/RFC-0027-slice-4-domain-model-vocabulary-review-state.md`
- `docs/rfcs/RFC-0027-slice-5-evidence-packet-redaction-projection.md`
- `docs/rfcs/RFC-0027-slice-6-guardrail-unsupported-evidence-engine.md`
- `docs/rfcs/RFC-0027-slice-7-lotus-ai-workflow-pack-model-risk-controls.md`
- `docs/rfcs/RFC-0027-slice-8-copilot-run-review-audit-retention.md`
- `docs/rfcs/RFC-0027-slice-9-certified-advise-apis-openapi.md`

