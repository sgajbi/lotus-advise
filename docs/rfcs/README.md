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
| RFC-0023 | Grounded Advisory AI Narrative and Client-Ready Proposal Commentary | IMPLEMENTED for advisor-review narrative evidence; client-ready scope remains gated | Active advisor-review narrative evidence source of truth; Slices 0-10 complete source mapping, platform-scaffolding review, cleanup/structure, narrative contract baseline, data-product/supportability baseline, deterministic advisor-review artifact-path narrative, policy/disclosure/guardrail baseline, AI-assisted draft adapter baseline, proposal-version narrative review/replay baseline, decision-summary/alternatives/approval/limitation narrative integration, and certified API/OpenAPI baseline; Slice 10B closes standalone proposal-version narrative read and non-persistent regeneration APIs; Slice 11A adds reviewed narrative package propagation into report-request evidence; Slices 11B/11C close `lotus-report` package consumption and `lotus-render` portfolio-review advisory narrative rendering; Slice 11D closes `lotus-archive` support-safe reviewed narrative artifact summary storage; Slice 11E closes `lotus-gateway` product-facing reviewed-narrative posture and `lotus-workbench` Gateway-backed advisor-use proposal posture; Slice 11F promotes advisor-review narrative evidence as `ProposalNarrativeEvidence:v1` with trust telemetry, platform catalog/certification, and `/platform/capabilities` reviewed narrative evidence posture; Slice 12 adds stateful live narrative proof, deterministic guardrail-failure reproduction, optional AI-assisted validation where enabled, and governed Workbench `proposal.narrative_posture` screenshot proof; compliance-review, client-draft, client-ready publication, and client communication remain gated future scope | RFC-0006, RFC-0011, RFC-0013, RFC-0014, RFC-0015, RFC-0019, RFC-0020, RFC-0021, RFC-0022 | `docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md` |
| RFC-0024 | Advisor Proposal Memo and Evidence Pack | DRAFT - GOLD-STANDARD IMPLEMENTATION PLAN; Slices 0-4 implemented | Active crown-jewel feature roadmap; Slice 0 closes critical review, source map, and product-gap allocation as a non-claiming source-authority gate. Slice 1 closes platform-scaffolding review and records that existing platform/repo-native controls are sufficient before memo domain work. Slice 2 cleans the report-handoff boundary by moving reviewed narrative package rules out of the API service layer. Slice 3 declares proposed/blocked `AdvisoryProposalMemoEvidencePack:v1` data-product and trust-telemetry posture without capability promotion. Slice 4 persists an RFC-0024 memo source-readiness manifest over proposal evidence so missing `lotus-core`, `lotus-risk`, and `lotus-advise` facts become explicit `PENDING_REVIEW`, `BLOCKED`, or `NOT_AVAILABLE` posture. RFC-0024 remains the execution source and WTBD is closed historical context only; memo generation, memo APIs, memo persistence, report package, Gateway, Workbench, active data-product support, and client-ready memo claims remain planned until implementation-backed slices close. | RFC-0006, RFC-0011, RFC-0013, RFC-0019, RFC-0020, RFC-0021, RFC-0022, RFC-0023 | `docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md` |
| RFC-0025 | Enterprise Suitability and Best-Interest Policy Packs | DRAFT - GOLD-STANDARD IMPLEMENTATION PLAN | Active crown-jewel feature roadmap; RFC is the execution source and WTBD is closed historical context only | RFC-0010, RFC-0013, RFC-0015, RFC-0020, RFC-0021, RFC-0022, RFC-0024 | `docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md` |
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

## Not Yet Implemented

Open RFCs still relevant to the advisory roadmap:
- `RFC-0014`
- `RFC-0015`
- `RFC-0016`
- `RFC-0017`
- `RFC-0018`
- `RFC-0024`
- `RFC-0025`
- `RFC-0026`
- `RFC-0027`
- `RFC-0028`

Recommended near-term implementation order:
1. `RFC-0024` remaining implementation slices after Slice 0 source-map closure
2. `RFC-0025` enterprise suitability and best-interest policy packs
3. `RFC-0026` advisor cockpit operating workflow
4. `RFC-0027` governed advisory AI copilot
5. `RFC-0028` bank demo journey and client-ready proof
6. `RFC-0014` remaining replay and data-quality backbone deltas not already covered by current implementation
7. `RFC-0016` costs, fees, and transaction frictions
8. `RFC-0017` remaining execution-boundary stabilization deltas not already covered by current implementation

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
