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
| RFC-0023 | Grounded Advisory AI Narrative and Client-Ready Proposal Commentary | DRAFT - GOLD-STANDARD IMPLEMENTATION PLAN; Slices 0-3 implemented | Active crown-jewel feature roadmap; Slices 0-3 complete source mapping, platform-scaffolding review, cleanup/structure, and narrative contract baseline, but proposal narrative remains future implementation until later slices close | RFC-0006, RFC-0011, RFC-0013, RFC-0014, RFC-0015, RFC-0019, RFC-0020, RFC-0021, RFC-0022 | `docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md` |
| RFC-0024 | Advisor Proposal Memo and Evidence Pack | DRAFT - GOLD-STANDARD IMPLEMENTATION PLAN | Active crown-jewel feature roadmap; RFC is the execution source and WTBD is closed historical context only | RFC-0006, RFC-0011, RFC-0013, RFC-0019, RFC-0020, RFC-0021, RFC-0022, RFC-0023 | `docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md` |
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

## Not Yet Implemented

Open RFCs still relevant to the advisory roadmap:
- `RFC-0014`
- `RFC-0015`
- `RFC-0016`
- `RFC-0017`
- `RFC-0018`
- `RFC-0023`
- `RFC-0024`
- `RFC-0025`
- `RFC-0026`
- `RFC-0027`
- `RFC-0028`

Recommended near-term implementation order:
1. `RFC-0023` remaining implementation slices after Slice 0 source-map, Slice 1 platform-scaffolding, Slice 2 cleanup/structure, and Slice 3 contract-baseline closure
2. `RFC-0024` advisor proposal memo and evidence pack
3. `RFC-0025` enterprise suitability and best-interest policy packs
4. `RFC-0026` advisor cockpit operating workflow
5. `RFC-0027` governed advisory AI copilot
6. `RFC-0028` bank demo journey and client-ready proof
7. `RFC-0014` remaining replay and data-quality backbone deltas not already covered by current implementation
8. `RFC-0016` costs, fees, and transaction frictions
9. `RFC-0017` remaining execution-boundary stabilization deltas not already covered by current implementation

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
