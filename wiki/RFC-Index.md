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
- RFC-0024 advisor proposal memo and evidence pack
- RFC-0025 enterprise suitability and best-interest policy packs
- RFC-0026 advisor cockpit operating workflow
- RFC-0027 governed advisory AI copilot
- RFC-0028 bank demo journey and client-ready proof

## Important Interpretation

RFC-0023 through RFC-0028 are gold-standard implementation plans for the next advisory crown-jewel
roadmap. RFC-0023 is now implemented for governed advisor-review proposal narrative evidence and
defines the grounded narrative prerequisite consumed by proposal memo, policy, cockpit, copilot, and
demo work. RFC-0024 is the next recommended implementation slice.

RFC-0024 Slice 0 is implemented as a critical-review, source-map, and product-gap allocation gate.
It records memo source authorities, cross-repo ownership, required blocked states, and the first
bounded implementation direction. It does not implement advisor proposal memo generation, memo APIs,
memo persistence, memo report packages, Gateway/Workbench memo surfaces, or client-ready memo
publication.

RFC-0024 Slice 1 is implemented as a platform automation and scaffolding review. It records that
existing Lotus platform and repo-native controls are sufficient before memo domain work, rejects
one-off local memo scaffolding, and pins the controls later RFC-0024 slices must satisfy for API
quality, observability, test pyramid, data-product promotion, trust telemetry, live proof, and
documentation truth.

RFC-0024 Slice 2 is implemented as cleanup and structure work. It moves reviewed narrative
report-package business rules from the API service layer into the core proposal report-handoff
boundary and adds engine-level tests for source-backed package construction, review approval,
hash-continuity, and support-safe summaries. It does not implement or promote advisor proposal memo
support.

RFC-0024 Slice 3 is implemented as data-product and platform-hardening work. It declares proposed
`AdvisoryProposalMemoEvidencePack:v1` product identity and blocked trust telemetry so governance
controls can see the planned memo product boundary. It does not add memo routes, active mesh
policy, `/platform/capabilities` support, Gateway/Workbench memo support, or client-ready memo
publication.

RFC-0024 Slice 4 is implemented as upstream source evidence completion. Proposal evidence bundles
now include a persisted `rfc0024.memo-source-readiness.v1` manifest that attributes memo-critical
source families to `lotus-core`, `lotus-risk`, and `lotus-advise`, marks unsupported or incomplete
facts as `PENDING_REVIEW`, `BLOCKED`, or `NOT_AVAILABLE`, and keeps memo generation and client-ready
publication unpromoted.

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
is tracked separately in Slice 10B.

RFC-0023 Slice 10B is implemented as standalone narrative read and regeneration API work. It adds
exact persisted narrative reads and non-persistent advisor-review regeneration candidates under the
canonical proposal-version route family, with source hashes, replay path, material-change posture,
and explicit review-required/non-client-ready posture.

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

RFC-0023 Slice 11D is implemented as downstream archive realization work. `lotus-archive` stores a
support-safe `reviewed_advisory_narrative` metadata summary for rendered advisor-use
portfolio-review artifacts, requires approved advisor-review posture and `sha256:` source hashes,
rejects client-ready statuses, and records source events with reviewed narrative package lineage
without storing raw narrative sections separately.

RFC-0023 Slice 11E is implemented as Gateway and Workbench realization work. `lotus-gateway`
exposes product-facing reviewed-narrative posture through canonical `lotus-advise` review,
report-request, delivery-summary, and delivery-event APIs, while `lotus-workbench` renders the
Gateway-backed advisor-use proposal narrative posture without inferring narrative facts locally.

RFC-0023 Slice 11F is implemented as narrative data-product, trust-telemetry, and capability
promotion work. `lotus-advise` now declares `ProposalNarrativeEvidence:v1`, validates
advisor-review narrative trust telemetry against that declaration, and advertises
`advisory.proposals.reviewed_narrative_evidence` plus
`advisory_proposal_reviewed_narrative_evidence` in `/platform/capabilities`. `lotus-platform`
catalog and certification artifacts include the new product.

RFC-0023 Slice 12 is implemented as live validation, canonical proof, and operator-evidence
hardening. The live suite now creates stateful advisor-review narrative proposals from Lotus Core
context, validates immutable read, non-persistent regeneration, advisor-use review, reviewed
report-package request, replay evidence, guardrail failure reproduction, and optional
AI-assisted validation when enabled. Workbench canonical validation now proves
`proposal.narrative_posture` with a governed screenshot and panel-registry classification.

RFC-0023 Slice 13/14 is implemented as closure hardening and gold-standard review. It records that
RFC-0023 is not a full client-ready publication capability and hardens the review workflow so an
otherwise clean advisor-review narrative release request still cannot return
`APPROVED_FOR_CLIENT_READY`.

RFC-0023 is now implemented for artifact-path advisor-review narrative and proposal-version
review/replay evidence with decision-summary and alternatives-aware section rendering, and the
canonical API/OpenAPI surface is certified for standalone read, non-persistent regeneration,
review, and replay. Report requests can include a reviewed narrative package only when review
posture and hash continuity are sufficient, and the package can now flow through
`lotus-report`, `lotus-render`, `lotus-archive`, `lotus-gateway`, and `lotus-workbench` as
advisor-use product content and posture. Advisor-review narrative evidence now has data-product,
trust telemetry, platform catalog/certification, capability-discovery posture, live validation, and
governed canonical Workbench proof. Compliance-review, client-draft, client-ready artifact
publication, and client communication remain gated future scope for RFC-0024 through RFC-0028 or a
future explicitly approved implementation RFC; they are not supported RFC-0023 closure claims.

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
- `docs/rfcs/RFC-0023-slice-10B-standalone-narrative-read-regeneration-api.md`
- `docs/rfcs/RFC-0023-slice-11A-reviewed-narrative-report-request-package-propagation.md`
- `docs/rfcs/RFC-0023-slice-11B-11C-report-render-reviewed-narrative-realization.md`
- `docs/rfcs/RFC-0023-slice-11D-archive-reviewed-narrative-artifact-realization.md`
- `docs/rfcs/RFC-0023-slice-11E-gateway-workbench-reviewed-narrative-realization.md`
- `docs/rfcs/RFC-0023-slice-11F-narrative-data-product-trust-capability-promotion.md`
- `docs/rfcs/RFC-0023-slice-12-live-validation-canonical-proof-and-operator-evidence.md`
- `docs/rfcs/RFC-0023-slice-13-14-closure-hardening-and-review.md`
- `docs/rfcs/RFC-0024-slice-0-critical-review-source-map-and-product-gap-allocation.md`
- `docs/rfcs/RFC-0024-slice-1-platform-automation-and-scaffolding-review.md`
- `docs/rfcs/RFC-0024-slice-2-cleanup-and-structure.md`
- `docs/rfcs/RFC-0024-slice-3-data-product-and-platform-hardening.md`
- `docs/rfcs/RFC-0024-slice-4-upstream-source-evidence-completion.md`
