# RFC-0004: Iterative Advisory Proposal Workspace Contract

- Status: Proposed
- Date: 2026-02-24
- Owners: lotus-advise advisory workflow service
- Requires Approval From: lotus-advise maintainers

## Summary

`lotus-advise` already supports proposal simulation, artifact generation, workflow gates, and
proposal persistence.

Those capabilities are valuable, but they are still shaped more like request-response workflow APIs
than a true advisory workspace.

This RFC defines the next product layer:

1. a first-class iterative advisory proposal workspace,
2. optimized for advisor draft-edit-evaluate loops,
3. explicitly aligned to advisory-business workflows rather than rebalancing or DPM concepts,
4. designed to fit cleanly with `lotus-core`, `lotus-risk`, `lotus-report`, `lotus-ai`, and Lotus
   Workbench.

The target is not just a usable internal tool.

The target is a bank-grade advisory product surface that can credibly support:

1. relationship managers and advisors,
2. investment counselors and proposal reviewers,
3. risk and compliance control functions,
4. client-consent and execution-preparation workflows.

## Why This RFC Exists

Real advisory teams do not work only in one-shot simulation requests.

They need a workspace where an advisor can:

1. open a live portfolio context,
2. draft a proposal,
3. add, remove, or modify intended trades and cash movements,
4. see immediate portfolio-impact, suitability, and policy feedback,
5. compare iterations,
6. save progress,
7. route the finished proposal into approval, consent, reporting, and execution flows.

Today, `lotus-advise` has strong building blocks, but it still lacks that dedicated workspace
contract.

Without this RFC:

1. the service remains too API-transaction-oriented,
2. UI workflows will have to stitch together multiple low-level contracts,
3. stateful advisory iteration will remain harder to reason about than it should be,
4. future integration with `lotus-core`, `lotus-risk`, `lotus-report`, and `lotus-ai` will become
   harder to scale cleanly.

This RFC therefore follows the kind of standards expected in mature advisory platforms:

1. draft proposals must be explainable,
2. suitability and policy review must be evidence-backed,
3. iteration history must be auditable,
4. lifecycle handoff must preserve control and traceability,
5. user-facing contract design must be operationally ergonomic, not only technically correct.

## Problem Statement

The current advisory surface is missing a normalized workspace model for iterative draft building.

Examples of current friction:

1. proposal editing is not expressed as a dedicated workspace aggregate,
2. delta changes are not first-class advisory operations,
3. impact, violations, and recommendations are not yet normalized for per-iteration UI panels,
4. save/resume/compare workflows are not modeled as a single advisory-workspace contract,
5. stateful portfolio sourcing and stateless sandbox usage are not unified under one clear
   workspace shape.

## Goals

1. Add a dedicated advisory workspace contract for iterative proposal drafting.
2. Support both stateless and stateful advisory operation in the same workspace model.
3. Normalize impact, violations, and next-step guidance for UI consumption.
4. Keep the workspace deterministic, replayable, and audit-friendly.
5. Prepare `lotus-advise` to orchestrate upstream `lotus-core`, `lotus-risk`, optional
   `lotus-performance`, `lotus-report`, and `lotus-ai` capabilities without absorbing their domain
   ownership.
6. Make the workspace strong enough for real advisory operating teams, not only engineering demos.
7. Ensure the contract can support a marketable advisor experience in Lotus Workbench.

## Non-Goals

1. Re-implementing canonical portfolio simulation logic that belongs in `lotus-core`.
2. Re-implementing risk analytics that belong in `lotus-risk`.
3. Owning final client-ready reporting that belongs in `lotus-report`.
4. Turning `lotus-advise` into an OMS or discretionary portfolio-management service.
5. Building every future advisory feature in this RFC; this RFC focuses on the workspace backbone.

## Decision

`lotus-advise` will add a first-class iterative advisory proposal workspace contract.

This workspace will:

1. treat advisory draft state as a first-class domain object,
2. support repeated draft mutations and re-evaluation,
3. expose normalized advisor-facing impact and violation panels,
4. support both stateless and stateful portfolio sourcing,
5. transition cleanly into the existing persisted proposal lifecycle once a draft is ready.

The workspace will be advisory-first, not rebalance-first and not DPM-shaped.

## Operating Principles

The workspace should follow explicit operating principles that reflect industry-grade advisory
practice.

1. Advisor-first ergonomics:
   the contract should make common advisory tasks easy to express and inspect.
2. Control-first transparency:
   suitability, policy, and gating outcomes must be explicit, reviewable, and evidence-backed.
3. Deterministic evidence:
   the same proposal context and options must produce the same evaluation posture.
4. Clean ownership:
   `lotus-advise` orchestrates advisory workflow; it does not silently re-own upstream domain
   engines.
5. Audit-grade traceability:
   every important workspace transition must be reconstructable.
6. Gold-standard naming:
   public nouns, APIs, models, and storage concepts must reflect advisory business language.

## Primary Users and Workflow Roles

The workspace should be designed around real operating roles rather than a generic client.

Primary roles:

1. advisor or relationship manager,
2. investment counselor or proposal reviewer,
3. risk reviewer,
4. compliance reviewer,
5. operations or support user investigating workflow history.

The first implementation should optimize for the advisor role without losing the needs of the
review and control functions that sit around the advisor workflow.

## Advisory Workspace Model

The workspace should center around a small set of clear concepts.

### 1. Workspace Session

A workspace session represents an in-progress advisory draft for a portfolio or household context.

It should capture:

1. workspace identity,
2. portfolio or household context,
3. current draft proposal state,
4. source mode (`stateless` or `stateful`),
5. current evaluation summary,
6. lineage needed for replay and audit.

### 2. Draft Mutations

The workspace must treat draft mutations as first-class actions.

Examples:

1. add trade,
2. update trade,
3. remove trade,
4. add cash movement,
5. update cash movement,
6. remove cash movement,
7. update proposal options,
8. reset or fork draft state.

This is more useful than forcing clients to resubmit a full request for every small edit.

### 3. Evaluation Panels

The workspace should return normalized evaluation outputs for UI panels.

These should include:

1. portfolio impact summary,
2. suitability and policy issues,
3. gate and next-step guidance,
4. proposal completeness and blocking conditions,
5. optional advisory insights from downstream integrations,
6. reviewer-ready evidence summaries.

The response should be advisor-usable, not just engine-usable.

### 4. Compare and Replay

Advisors need to compare iterations and recover decision context.

The workspace should support:

1. current draft versus source portfolio,
2. current draft versus prior saved draft,
3. deterministic replay of the evaluation basis,
4. durable traceability for what changed and why.

### 5. Lifecycle Handoff

When a draft is ready, the workspace should hand off cleanly into formal proposal lifecycle APIs.

That means:

1. no duplication of lifecycle ownership,
2. clear transition from draft workspace to persisted proposal version,
3. preserved evidence and lineage.

## Operating Modes

The workspace should support both advisory operating modes.

### Stateless Mode

In stateless mode:

1. the caller provides portfolio state directly,
2. the workspace is ideal for sandboxing, external integrations, and deterministic replay,
3. the resolved evaluation context must still be returned explicitly for auditability.

### Stateful Mode

In stateful mode:

1. the caller provides identifiers such as portfolio, household, mandate, and as-of context,
2. `lotus-advise` resolves canonical advisory context through `lotus-core` and related services,
3. the resolved context must be returned explicitly so the draft can be audited and reproduced.

This dual-mode model should be part of the same workspace design, not split into unrelated APIs.

## Architecture Direction

### Advisory-First Domain Boundary

The workspace must remain within advisory-service ownership.

`lotus-advise` should own:

1. advisory draft workspace state,
2. draft mutation orchestration,
3. normalized advisory evaluation assembly,
4. lifecycle handoff into persisted proposal flows.

It should not absorb upstream domain math just because the workspace needs those outputs.

### Upstream Integration Model

The workspace should integrate with other Lotus apps through explicit seams.

Expected roles:

1. `lotus-core` for canonical portfolio sourcing and simulation authority,
2. `lotus-risk` for risk and policy analytics,
3. `lotus-report` for report-ready advisory outputs,
4. `lotus-ai` for governed AI-assisted advisory workflows,
5. `lotus-gateway` and `lotus-workbench` as the primary UI-facing consumers.

`lotus-performance` remains optional for the first workspace slices, but the contract should not
block future integration for performance context, benchmark context, or attribution-aware proposal
storytelling.

### Determinism and Replay

The workspace must preserve deterministic evaluation behavior.

Required behavior:

1. stable draft mutation semantics,
2. explicit resolved context,
3. repeatable evaluation with the same inputs and options,
4. no hidden dependence on unstable UI-only state.

### API Contract Quality

The workspace APIs must meet Lotus API quality standards.

Required behavior:

1. every operation has a summary and description,
2. every field has type, description, and example,
3. every request and response includes meaningful advisory examples,
4. vocabulary follows Lotus platform standards governed by `lotus-platform`,
5. public naming remains advisory-business aligned.
6. operations and schemas are complete enough to be usable without source-code spelunking.

## AI Direction

The workspace should be designed so that `lotus-ai` can add differentiated advisory assistance
without taking over deterministic decisioning.

The intended pattern is:

1. deterministic workspace facts come from `lotus-advise` and upstream Lotus domain services,
2. `lotus-ai` can generate advisor assistance on top of those facts,
3. AI outputs must remain reviewable, evidence-backed, and clearly secondary to deterministic
   domain truth.

High-value future examples include:

1. proposal rationale drafting,
2. meeting-prep summaries,
3. note-to-draft proposal assistance,
4. explanation of policy or suitability breaches,
5. client-communication drafting from approved facts.

## Data and Persistence Requirements

1. Workspace state must contain advisory-only data.
2. Draft mutation history must be audit-friendly.
3. The database model must remain clean and avoid reintroducing DPM-era concepts.
4. Replay and comparison data must be explicit rather than inferred from loosely related records.
5. Stateful resolution metadata must be preserved so saved drafts remain explainable.
6. Stored data must be intentionally minimal and advisory-relevant, with no stale legacy scope.

## Delivery Slices

This RFC will be implemented slice by slice within the same RFC.

### Slice 1: Workspace Contract Foundation

Status:

1. implemented

Outcome:

1. a first-class advisory workspace session model exists,
2. the service exposes clean advisory workspace vocabulary,
3. request and response contracts are fully documented and Lotus-branded.

Acceptance gate:

1. workspace session contract is explicit and advisory-business aligned,
2. contract supports both stateless and stateful modes,
3. field-level descriptions and examples are complete,
4. naming is clean and free of DPM or rebalance leakage,
5. the contract is strong enough for gateway and workbench adoption without ad hoc client-side
   patching.

### Slice 2: Draft Mutation and Re-Evaluation Loop

Status:

1. implemented

Outcome:

1. draft mutations become first-class operations,
2. the service can add, update, remove, and re-evaluate draft components,
3. evaluation outputs are normalized for UI iteration.

Acceptance gate:

1. mutation behavior is deterministic,
2. evaluation responses are modular and UI-ready,
3. meaningful tests prove add/update/remove and re-evaluate behavior,
4. no low-value or superficial test coverage is accepted,
5. impact, issues, and next-step guidance are understandable to both advisors and reviewers.

### Slice 3: Save, Resume, Compare, and Replay

Status:

1. implemented

Outcome:

1. draft workspaces can be saved and resumed,
2. iteration comparison is available,
3. replay-safe evidence exists for workspace decisions.

Acceptance gate:

1. compare semantics are explicit and understandable,
2. replay uses durable resolved context and draft lineage,
3. persistence remains advisory-only and schema-clean,
4. documentation explains save/resume/compare behavior clearly,
5. support and control users can inspect saved workspace history without hidden joins or ambiguous
   reconstruction logic.

### Slice 4: Lifecycle Handoff and Upstream Integration Hardening

Outcome:

1. workspace drafts transition cleanly into persisted proposal lifecycle,
2. upstream seams are strong enough for stateful advisory operation,
3. downstream consumers can rely on stable workspace outputs.

Acceptance gate:

1. lifecycle handoff does not duplicate ownership with proposal persistence,
2. `lotus-core` and `lotus-risk` integration boundaries stay clean,
3. the codebase becomes more modular, not more entangled,
4. build, tests, and retained advisory features validate cleanly,
5. the resulting surface feels like an advisory product workflow, not an internal orchestration
   artifact.

## Risks

1. If the workspace is modeled too generically, it will feel like infrastructure rather than an
   advisory product surface.
2. If mutation contracts are not normalized, the UI will have to reconstruct too much state.
3. If stateful and stateless modes diverge too much, the system will become harder to maintain.
4. If persistence is introduced carelessly, the database can accumulate unnecessary or legacy scope.
5. If upstream seams are vague, `lotus-advise` may accidentally re-own simulation or risk logic.
6. If the contract is under-specified, gateway and workbench will be forced to compensate in
   inconsistent ways.

## Success Criteria

This RFC is successful when:

1. advisors have a real iterative workspace model rather than only one-shot workflow endpoints,
2. the workspace feels native to advisory business workflows,
3. stateful and stateless use cases are supported through one coherent contract,
4. Lotus Workbench and gateway can consume the workspace with minimal contract stitching,
5. the codebase remains cleaner, more modular, and more advisory-specific after implementation,
6. the resulting workspace is credible as a bank-grade, marketable advisory capability rather than
   only an engineering improvement.
