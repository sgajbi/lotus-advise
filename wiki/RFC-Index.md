# RFC Index

## Governing Rule

Service-specific implementation RFCs live in this repository. Cross-cutting or multi-service RFCs
belong in `lotus-platform`.

## Active Implemented Backbone

The current implemented advisory backbone is anchored by:

- RFC-0003 advisory proposal workflow coverage hardening
- RFC-0004 iterative advisory proposal workspace contract
- RFC-0005 advisory PostgreSQL runtime and persistence cutover
- RFC-0006 target operating model and integration architecture
- RFC-0007 proposal simulation MVP
- RFC-0008 proposal auto-funding
- RFC-0009 drift analytics
- RFC-0010 suitability scanner v1
- RFC-0011 proposal artifact
- RFC-0012 workflow gates and next-step semantics
- RFC-0013 persistence, workflow lifecycle, and audit model
- RFC-0019 authoritative context, durable runtime, and workspace closure
- RFC-0020 canonical allocation and risk-lens convergence
- RFC-0021 proposal decision summary and enterprise suitability policy
- RFC-0022 proposal alternatives and portfolio construction workbench

## Active Future Work

The repository RFC index currently keeps these as active future work:

- RFC-0014 data quality, snapshots, and replayability
- RFC-0015 jurisdiction and policy packs
- RFC-0016 costs, fees, and transaction frictions
- RFC-0017 execution integration interface
- RFC-0018 monitoring, surveillance, and post-trade controls
- RFC-0023 grounded advisory AI narrative and client-ready proposal commentary
- RFC-0024 advisor proposal memo and evidence pack
- RFC-0025 enterprise suitability and best-interest policy packs
- RFC-0026 advisor cockpit operating workflow
- RFC-0027 governed advisory AI copilot
- RFC-0028 bank demo journey and client-ready proof

## Important Interpretation

RFC-0023 through RFC-0028 are gold-standard implementation plans for the next advisory crown-jewel
roadmap. RFC-0023 is now the recommended first implementation slice because it defines the grounded
narrative prerequisite consumed by proposal memo, policy, cockpit, copilot, and demo work.

RFC-0023 Slice 0 is implemented as a critical-review, source-map, and product-gap allocation gate.
It records source authorities, cross-repo ownership, and the first bounded implementation direction.
It does not implement generated proposal narrative.

RFC-0023 Slice 1 is implemented as a platform automation and scaffolding review. It records that
existing Lotus platform automation is sufficient for the next RFC-0023 slices and that no
`lotus-platform` code change is required before cleanup and contract work begins.

RFC-0023 Slice 2 is implemented as cleanup and structure work. It moves workspace-rationale
evidence construction into core workspace code, keeps the API service thin, removes a premature
client-ready OpenAPI wording claim, and does not promote proposal narrative support.

RFC-0023 Slice 3 is implemented as current-state assessment and narrative contract baseline work.
It maps current artifact, proposal detail, workspace, lifecycle, replay, decision-summary, and
alternatives evidence, defines an additive `proposal_narrative` contract baseline, and proves no
public API v2 is needed before implementation-bearing slices.

RFC-0023 Slice 4 is implemented as data-product and supportability baseline work. It records that
proposal narrative is not yet promoted as a domain data product, trust-telemetry fixture, or
`/platform/capabilities` feature because deterministic advisor-review narrative readiness has not
been implemented yet.

RFC-0023 Slice 5 is implemented as grounding-packet and deterministic-template baseline work. It
adds opt-in deterministic `ADVISOR_REVIEW` narrative in the proposal artifact path without AI
dependency. Standalone narrative endpoints, persistence, replay, review approval, AI-assisted
drafts, client-ready commentary, report/render/archive integration, data-product promotion, and
`/platform/capabilities` narrative rows remain gated by later slices.

RFC-0023 Slice 6 is implemented as narrative-policy, disclosure, and guardrail baseline work. It
adds deterministic policy metadata, approved disclosure selection, unsupported-claim guardrails,
and client-ready policy blockers to the artifact-path narrative response. Standalone narrative
endpoints, persistence, replay, review approval, client-ready commentary,
report/render/archive integration, data-product promotion, and `/platform/capabilities` narrative
rows remain gated by later slices.

RFC-0023 Slice 7 is implemented as a narrow lotus-ai adapter and AI-assisted advisor-review draft
baseline. It adds opt-in `AI_ASSISTED_DRAFT` narrative in the proposal artifact path, sends only
structured grounding packet, resolved policy, requested sections, approved instructions, and source
refs to the workflow-pack adapter, records AI lineage or deterministic fallback reason, and runs AI
text through the same unsupported-claim guardrails before returning the draft. Standalone narrative
endpoints, persistence, replay, review approval, client-ready commentary, report/render/archive
integration, data-product promotion, and `/platform/capabilities` narrative rows remain gated by
later slices.

RFC-0023 Slice 8 is implemented as a proposal-version review, persistence, idempotency, and replay
baseline. It persists narrative JSON with immutable proposal versions when lifecycle create/version
requests include `narrative_request`, records append-only `NARRATIVE_REVIEWED` review events for
approve, reject, and regeneration-request decisions, supports idempotent review replay and payload
drift conflicts, and returns exact persisted narrative plus latest review evidence from replay
endpoints. Client-ready commentary, report/render/archive integration, Gateway and Workbench
surfaces, data-product promotion, trust telemetry, and `/platform/capabilities` narrative rows
remain gated by later slices.

RFC-0023 Slice 9 is implemented as alternatives, decision-summary, and policy-evidence integration
work. It enriches advisor-review narrative sections with RFC-0021 decision-summary posture,
blockers, approval/remediation requirements, material changes, RFC-0022 selected-alternative
tradeoffs, rejected-candidate evidence, and risk/suitability limitations.

RFC-0023 Slice 10 is implemented as certified API and OpenAPI baseline work. It certifies the
existing additive advisor-review narrative API shape, canonical proposal-version review route,
proposal/async replay evidence routes, response documentation, idempotency header guidance,
stale-route absence, and material returned-field coverage. Standalone narrative read/regeneration
routes, client-ready commentary, report/render/archive integration, Gateway and Workbench surfaces,
data-product promotion, trust telemetry, and `/platform/capabilities` narrative rows remain gated by
later slices.

RFC-0023 Slice 11A is implemented as reviewed narrative report-request package propagation
baseline work. It adds explicit `include_reviewed_narrative` support to proposal report requests,
requires the selected immutable proposal version to have an `APPROVED_FOR_ADVISOR_USE` narrative
review with matching source hash, propagates a compact source-backed narrative package to the
report seam, and persists a package summary in report-request delivery evidence.

RFC-0023 Slices 11B and 11C are implemented as downstream report and render realization work.
`lotus-report` consumes and snapshots the reviewed advisory narrative package, projects an
immutable render payload into `report_data.reviewed_advisory_narrative`, and preserves package
lineage, disclosure refs, guardrail posture, limitations, review state, policy version, source
hashes, and advisor-use restrictions. `lotus-render` consumes that payload and renders an optional
portfolio-review v1 advisory narrative page when the package status is `included`, while omitting
the page for reports without a reviewed package.

RFC-0023 is now implemented for artifact-path advisor-review narrative and proposal-version
review/replay evidence with decision-summary and alternatives-aware section rendering, and the
canonical API/OpenAPI surface is certified. Report requests can include a reviewed narrative package
only when review posture and hash continuity are sufficient, and the package can now flow through
`lotus-report` and `lotus-render` as advisor-use report content. `lotus-archive`, Gateway,
Workbench, client-ready artifact publication, data-product promotion, trust telemetry, and
`/platform/capabilities` narrative rows remain planned future work until the remaining RFC-0023
slices are merged to `main`, validated, and published with implementation-backed feature truth.

## Source Index

Use `docs/rfcs/README.md` as the authoritative repository RFC disposition index.

Implementation evidence:
- `docs/rfcs/RFC-0023-slice-0-critical-review-source-map-and-product-gap-allocation.md`
- `docs/rfcs/RFC-0023-slice-1-platform-automation-and-scaffolding-review.md`
- `docs/rfcs/RFC-0023-slice-2-cleanup-and-structure.md`
- `docs/rfcs/RFC-0023-slice-3-current-state-assessment-and-narrative-contract-baseline.md`
- `docs/rfcs/RFC-0023-slice-4-data-product-and-supportability-baseline.md`
- `docs/rfcs/RFC-0023-slice-5-grounding-packet-and-deterministic-template-baseline.md`
- `docs/rfcs/RFC-0023-slice-6-narrative-policy-disclosure-and-guardrail-framework.md`
- `docs/rfcs/RFC-0023-slice-7-lotus-ai-adapter-and-ai-assisted-draft-baseline.md`
- `docs/rfcs/RFC-0023-slice-8-review-workflow-persistence-idempotency-artifact-and-replay.md`
- `docs/rfcs/RFC-0023-slice-9-alternatives-decision-summary-and-policy-evidence-integration.md`
- `docs/rfcs/RFC-0023-slice-10-certified-api-and-openapi.md`
- `docs/rfcs/RFC-0023-slice-11A-reviewed-narrative-report-request-package-propagation.md`
- `docs/rfcs/RFC-0023-slice-11B-11C-report-render-reviewed-narrative-realization.md`
