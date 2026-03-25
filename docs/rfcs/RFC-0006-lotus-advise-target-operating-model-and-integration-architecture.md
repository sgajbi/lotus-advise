# RFC-0006: lotus-advise Target Operating Model and Integration Architecture

- Status: Proposed
- Date: 2026-03-25
- Owners: lotus-advise
- Requires Approval From: lotus-advise maintainers
- Depends On: RFC-0013, RFC-0003, RFC-0004

## Summary

`lotus-advise` should become the advisory workflow and orchestration service for the Lotus estate,
not a second portfolio simulation engine, not a second risk engine, and not a mixed-scope
repository with legacy ownership drift.

This RFC defines the target architecture for `lotus-advise`:

1. advisory-business workflow ownership stays in `lotus-advise`,
2. canonical portfolio state and simulation authority stay in `lotus-core`,
3. risk calculations stay in `lotus-risk`,
4. report-generation ownership stays in `lotus-report`,
5. governed AI runtime and controls stay in `lotus-ai`,
6. common vocabulary, API quality, and platform standards stay governed by `lotus-platform`.

This RFC is the architecture program for making `lotus-advise` a bank-grade, marketable advisory
application that fits cleanly into the Lotus ecosystem.

It also defines delivery slices inside one RFC so the architecture can evolve without proliferating
child RFCs.

## Why This RFC Exists

`lotus-advise` has valuable advisory capabilities today, but its architecture still risks drifting
toward the wrong shape if we do not set a strong operating model.

Without this RFC:

1. service boundaries remain blurry,
2. advisory workflows risk accumulating duplicate simulation or risk logic,
3. legacy scope can continue leaking into advisory runtime and docs,
4. stateful portfolio-sourced advisory workflows will be harder to implement cleanly,
5. platform integrations may become ad hoc rather than bank-grade and governable.

This RFC exists to stop that drift and define the target architecture clearly enough that we can
build with confidence.

## Problem Statement

The current repository still reflects earlier structure and assumptions that are no longer right
for the target product.

Current problems include:

1. architecture still carries traces of older mixed-scope or DPM-adjacent history,
2. `lotus-advise` has not yet fully converged on orchestrating upstream domain authorities,
3. the service needs a stronger model for stateless and stateful operation,
4. readiness and capability truth need to become dependency-aware rather than locally asserted,
5. AI opportunities need to be framed as governed assistance rather than domain-logic replacement.

If left unresolved, `lotus-advise` risks becoming a hard-to-maintain orchestration layer with
unclear ownership, inconsistent product contracts, and weak platform discipline.

## Goals

1. Define the authoritative service boundary for `lotus-advise`.
2. Define the target integration model across `lotus-core`, `lotus-risk`, `lotus-report`,
   optional `lotus-performance`, `lotus-ai`, `lotus-gateway`, and `lotus-workbench`.
3. Establish a clean stateless and stateful advisory operating model.
4. Make `lotus-advise` advisory-first, not rebalance-first and not DPM-shaped.
5. Keep vocabulary, API standards, and platform rules aligned with `lotus-platform`.
6. Define architecture slices that can be implemented progressively without weakening the target
   design.
7. Keep the codebase, docs, and persistence model clean enough for a gold-standard advisory app.

## Non-Goals

1. Defining every future API payload in this RFC.
2. Replacing `RFC-0004`, which remains the detailed workspace product contract.
3. Replacing implementation RFCs for reporting, execution, costs, policy packs, or surveillance.
4. Re-implementing upstream domain ownership inside `lotus-advise`.
5. Forcing optional `lotus-performance` integration where no advisory workflow needs it yet.

## Decision

`lotus-advise` will be the advisory workflow and orchestration service in the Lotus platform.

Its role is to own:

1. advisory workspace and draft workflow,
2. proposal lifecycle and workflow transitions,
3. advisory-facing orchestration across upstream domain services,
4. explanation assembly for advisors, reviewers, and operations,
5. execution handoff readiness and advisory audit correlation.

It will not own:

1. canonical portfolio state,
2. authoritative portfolio simulation math,
3. risk engines,
4. report-generation ownership,
5. AI runtime and governance infrastructure.

The service must remain platform-governed, bank-grade, and modular enough to take to market as a
serious advisory product.

## Operating Principles

1. Advisory-first product design:
   contracts, modules, and naming must reflect advisory workflows and business language.
2. Clean domain ownership:
   `lotus-advise` orchestrates advisory workflow and does not silently absorb upstream engines.
3. Deterministic evidence:
   evaluation posture, workflow routing, and advisory outcomes must be replayable and auditable.
4. Platform governance:
   cross-app vocabulary, OpenAPI standards, and shared engineering rules come from
   `lotus-platform`.
5. Bank-grade control posture:
   readiness, reviewability, auditability, and lifecycle traceability must be first-class.
6. Modular delivery:
   architecture slices should leave the repository cleaner and more understandable after each
   change.

## Service Mission and Ownership

`lotus-advise` is the advisory workflow service for:

1. advisor proposal drafting and evaluation orchestration,
2. proposal workflow gates and next-step routing,
3. proposal versioning, approvals, and client-consent workflow,
4. execution handoff readiness and advisory execution-state correlation,
5. advisor and reviewer explanation assembly.

`lotus-advise` owns:

1. advisory workspace sessions and draft mutations,
2. proposal drafts and immutable proposal versions,
3. workflow decisions derived from upstream evidence,
4. orchestration of upstream service calls for advisory workflows,
5. advisory-facing explainability and evidence assembly,
6. advisory execution handoff coordination.

`lotus-advise` does not own:

1. canonical positions, cash ledgers, transactions, valuations, or benchmark source data,
2. long-term authoritative simulation ownership if `lotus-core` already provides it,
3. risk calculations that belong in `lotus-risk`,
4. final reporting payload ownership that belongs in `lotus-report`,
5. shared AI runtime, retrieval, provider, safety, or rollout governance owned by `lotus-ai`.

## Integration Boundaries

### lotus-core

`lotus-core` is the authoritative dependency for:

1. canonical portfolio snapshot assembly,
2. holdings, transactions, cash, valuation, and benchmark context,
3. stateful portfolio sourcing by identifiers and as-of date,
4. canonical portfolio simulation for advisory before/after evaluation.

Target rule:

`lotus-advise` should reuse `lotus-core` simulation capability rather than maintain long-term
duplicate simulation ownership.

### lotus-risk

`lotus-risk` owns all risk-related calculations consumed by advisory workflows, including:

1. concentration and issuer exposure,
2. scenario and factor exposures,
3. stress and risk-limit checks,
4. pre-trade and post-simulation risk analytics,
5. before/after risk deltas.

`lotus-advise` may orchestrate, present, route, and explain those results, but it must not become
a second risk engine.

### lotus-report

`lotus-report` owns portfolio review and reporting payload generation.

`lotus-advise` may request, reference, or package report outputs in workflow context, but the
reporting domain remains owned by `lotus-report`.

### lotus-performance

`lotus-performance` is optional for the early architecture slices.

It becomes relevant when advisory workflows clearly benefit from:

1. return context,
2. benchmark-relative context,
3. contribution or attribution context,
4. performance-aware proposal storytelling.

The architecture must support this seam without making it mandatory prematurely.

### lotus-ai

`lotus-ai` is the governed AI dependency for advisory-assistive workflows.

`lotus-ai` should provide:

1. runtime execution,
2. prompt and rollout governance,
3. retrieval and grounding infrastructure,
4. safety controls,
5. AI audit and observability.

`lotus-advise` remains the advisory domain owner and should use `lotus-ai` to make workflows more
useful, not less deterministic.

### lotus-gateway and lotus-workbench

`lotus-gateway` and `lotus-workbench` are the primary UI-facing consumers of `lotus-advise`.

Architecture implication:

1. `lotus-advise` contracts must be strong enough for gateway and workbench adoption,
2. the UI should not be forced to compensate for under-specified or engineering-centric contracts,
3. normalized advisory responses should be designed for product workflows, not only backend purity.

## Operating Modes

`lotus-advise` must support two explicit operating modes.

### Stateless Mode

Purpose:

1. deterministic replay,
2. sandbox and what-if workflows,
3. external or partner integrations,
4. targeted testing and reproducibility.

In stateless mode, the caller provides advisory evaluation inputs directly.

Typical stateless inputs include:

1. portfolio snapshot,
2. market-data snapshot,
3. restrictions or shelf metadata,
4. proposal deltas,
5. optional reference model or benchmark context.

### Stateful Mode

Purpose:

1. production advisory workflows,
2. live portfolio review in Lotus applications,
3. advisor-driven proposal creation from system-of-record data.

In stateful mode, `lotus-advise` receives identity and selection inputs, then resolves canonical
context through upstream services, especially `lotus-core`.

Typical stateful inputs include:

1. `portfolio_id`,
2. `household_id` where supported,
3. `as_of`,
4. proposal deltas or overrides,
5. optional benchmark, mandate, policy, or scenario selectors.

### Required Contract Direction

All new advisory evaluation contracts should converge on:

1. `input_mode: "stateless" | "stateful"`,
2. `stateless_input`,
3. `stateful_input`,
4. explicit `resolved_context` in responses,
5. stable lineage references to upstream snapshot identifiers and dependency versions.

## Platform Governance Baseline

`lotus-advise` must conform to cross-application governance defined in `lotus-platform`.

This includes:

1. canonical domain vocabulary,
2. cross-app API naming rules,
3. OpenAPI quality requirements,
4. API vocabulary inventory governance,
5. dependency hygiene and security standards,
6. migration, durability, testing, and observability standards where applicable.

Rule:

`lotus-advise` may define advisory-specific concepts, but it must not invent conflicting local
aliases for platform-wide concepts that already have canonical Lotus terms.

## API Documentation and Contract Quality

All architecture work and implementation slices under this RFC must preserve Lotus API quality.

Minimum requirements:

1. every operation has `summary`, `description`, tags, and documented success and error responses,
2. every request and response field has type, description, and example,
3. every schema has a purpose statement and meaningful request/response examples,
4. examples must be Lotus-branded and advisory-business relevant,
5. OpenAPI and vocabulary governance should fail when required descriptions or examples are missing.

The resulting API surface should be usable without source-code spelunking.

## AI Direction

AI in `lotus-advise` should be advisor-assistive, evidence-grounded, and operationally governed.

Target AI feature families include:

1. proposal rationale generation from deterministic facts,
2. meeting-prep summaries,
3. note-to-proposal drafting assistance,
4. policy and exception explanation,
5. client communication drafting,
6. scenario exploration assistance,
7. reviewer copilot flows.

Guardrails:

1. AI must not silently replace deterministic portfolio, risk, or workflow truth,
2. evidence references must be retained for AI-assisted workflow outputs,
3. final domain decisions remain grounded in deterministic service outputs and policy gates.

## Capability and Readiness Model

The service must evolve from local flag truth toward dependency-aware capability truth.

Target dimensions include:

1. `feature_enabled`,
2. `operational_ready`,
3. `degraded`,
4. `dependency_requirements`,
5. `dependency_status`,
6. `fallback_mode`,
7. `degraded_reason`.

Examples:

1. advisory workspace can be enabled while stateful sourcing is degraded,
2. proposal lifecycle can be enabled while risk enrichment is unavailable,
3. AI drafting can be enabled only for specific tenants or workflows.

## Target Internal Architecture

The target internal architecture should include these clear areas:

1. `workspace`
   - draft sessions
   - iterative mutations
   - compare and re-evaluate flows
2. `proposal_lifecycle`
   - immutable versions
   - approvals
   - consent
   - lifecycle transitions
3. `integration_orchestrator`
   - `lotus-core` adapters
   - `lotus-risk` adapters
   - `lotus-report` adapters
   - optional `lotus-performance` adapters
   - `lotus-ai` adapters
   - execution adapters
4. `capability_and_readiness`
   - dependency-aware capability truth
   - degraded-mode diagnostics
5. `execution_handoff`
   - proposal-to-execution request lifecycle
   - execution-state aggregation
6. `explainability`
   - advisor and reviewer explanation assembly

## Scalability and Microservice Rules

`lotus-advise` must be designed for:

1. stateless API horizontal scaling,
2. async offload for heavier orchestration,
3. replay-safe request and mutation persistence,
4. explicit dependency timeouts and degraded-mode handling,
5. no shared-database coupling with other services,
6. append-only or immutable records for critical lifecycle and audit paths,
7. operational truth based on dependency reality rather than local optimism.

## Data and Cleanup Rules

The repository and persistence model must remain advisory-only.

This includes:

1. removing stale legacy runtime remnants that no longer belong to advisory,
2. removing or rewriting active docs that imply mixed ownership,
3. renaming APIs, docs, and modules where needed to reflect advisory-only ownership,
4. preserving historical artifacts only where needed for traceability,
5. keeping the database intentionally minimal and advisory-relevant.

No new work under this RFC should reintroduce DPM-era structure, language, or persistence scope.

## Delivery Slices

This RFC will be implemented slice by slice within the same RFC.

### Slice 1: Advisory-Only Architecture Reset and Integration Seams

Status:

1. implemented

Outcome:

1. stale active runtime remnants are removed from the advisory service,
2. repository and runtime language are made advisory-only,
3. initial integration seams exist for `lotus-core`, `lotus-risk`, `lotus-report`, `lotus-ai`,
   and optional `lotus-performance`,
4. a readiness-focused seam exists for dependency-aware capability truth,
5. docs and structure are aligned to platform vocabulary and standards.

Implementation shape:

1. active legacy runtime remnants are removed from the current source layout,
2. repository-overview and architecture docs present `lotus-advise` as advisory-only,
3. explicit seam packages exist for key Lotus dependencies,
4. readiness-related logic has a clear home instead of being spread through unrelated modules,
5. naming and directory structure better reflect advisory ownership.

Acceptance gate:

1. active non-advisory remnants are removed from current runtime structure,
2. advisory-only ownership is clear in repository docs and architecture language,
3. integration seam packages or equivalent adapter boundaries exist,
4. capability/readiness has an explicit implementation seam,
5. platform vocabulary and documentation standards are respected,
6. the slice leaves the codebase cleaner without introducing behavior drift.

Out of scope:

1. stateful sourcing contract redesign,
2. simulation authority cutover,
3. live risk enrichment cutover,
4. AI workflow delivery,
5. major client-facing workflow redesign.

### Slice 2: Operating Mode Contract and Context Resolution

Outcome:

1. advisory contracts support both `stateless` and `stateful` modes,
2. stateful sourcing flows cleanly from Lotus system-of-record services,
3. `resolved_context` and lineage become first-class advisory outputs.

Implementation shape:

1. contract vocabulary is standardized around `input_mode`, `stateless_input`, `stateful_input`,
   and `resolved_context`,
2. stateful inputs use canonical Lotus identity fields,
3. response payloads explicitly show what upstream context was resolved,
4. request and response examples make the difference between stateless and stateful usage obvious.

Acceptance gate:

1. `input_mode`, `stateless_input`, `stateful_input`, and `resolved_context` are explicit,
2. contracts are fully documented and Lotus-branded,
3. stateful sourcing is auditable and replay-friendly,
4. the contract is usable by gateway and workbench without ad hoc patching,
5. stateless and stateful flows do not fork into inconsistent business semantics.

Out of scope:

1. full simulation authority migration,
2. deep workspace mutation flows,
3. execution connectors,
4. report payload ownership changes.

### Slice 3: Upstream Authority Realignment

Outcome:

1. simulation authority converges toward `lotus-core`,
2. risk authority converges toward `lotus-risk`,
3. duplicate long-term ownership is removed from `lotus-advise`.

Implementation shape:

1. `lotus-advise` integrates with `lotus-core` simulation through explicit adapters,
2. risk enrichment paths move behind `lotus-risk` boundaries,
3. transitional compatibility bridges are reduced or retired deliberately,
4. retained advisory behaviors are validated against the new upstream authority model.

Acceptance gate:

1. `lotus-advise` no longer acts as a long-term duplicate simulation or risk owner,
2. orchestration boundaries are explicit and modular,
3. retained behavior is validated with meaningful tests,
4. migration remains product-safe and explainable,
5. operational fallback and degradation behavior are explicit when dependencies are unavailable.

Out of scope:

1. final reporting completion,
2. full execution-state lifecycle,
3. broad AI product rollout.

### Slice 4: Workspace, AI, and Readiness Hardening

Outcome:

1. the advisory workspace runs on top of the target architecture,
2. AI-assisted workflows can be introduced safely through `lotus-ai`,
3. readiness and degraded-mode truth are stronger and more operationally honest.

Implementation shape:

1. `RFC-0004` workspace contracts are implemented on the architecture seams defined here,
2. AI-assistive features consume deterministic advisory facts rather than bypassing them,
3. capability responses distinguish feature enablement from operational readiness,
4. degraded and fallback states are surfaced in a way the UI and operators can trust.

Acceptance gate:

1. `RFC-0004` workspace direction fits cleanly into the architecture,
2. AI remains evidence-grounded and governed,
3. capability truth reflects dependency reality,
4. the codebase becomes more modular, not more entangled,
5. advisory users and control users can both understand the resulting workflow posture.

Out of scope:

1. final production hard cutover,
2. long-tail advisory feature families beyond the scoped workspace and readiness needs.

### Slice 5: Reporting, Execution, and Production Completion

Outcome:

1. reporting and execution seams are completed,
2. advisory production posture is stronger end to end,
3. the service is operationally credible as a marketable advisory platform capability.

Implementation shape:

1. reporting seams are completed without moving reporting ownership into `lotus-advise`,
2. execution handoff and execution-state correlation are completed in advisory-owned boundaries,
3. operational validation is tightened across docs, tests, build, and production posture,
4. the service is prepared for hardening steps such as final runtime cutovers and broader rollout.

Acceptance gate:

1. reporting ownership remains in `lotus-report`,
2. execution handoff and state correlation are explicit and auditable,
3. production-readiness and observability expectations validate cleanly,
4. the resulting platform fit is bank-grade rather than merely functional,
5. the service can be presented as a serious advisory product capability with clean boundaries and
   operational credibility.

## Test and Validation Expectations

Implementation under this RFC should include:

1. unit tests for mode resolution and adapter orchestration,
2. integration tests for `lotus-core` sourcing and simulation flows,
3. integration tests for `lotus-risk` enrichment paths,
4. readiness and degraded-mode validation under dependency failure,
5. end-to-end tests through `lotus-gateway` and `lotus-workbench` where applicable,
6. audit and replay validation for both operating modes,
7. OpenAPI and vocabulary conformance validation against platform governance,
8. schema and operation documentation validation for descriptions, examples, and branding quality.

Tests must be meaningful and aligned to retained advisory features, never superficial.

## Risks

1. If service boundaries are not enforced, `lotus-advise` will accumulate duplicate domain logic.
2. If stateful and stateless modes diverge too much, the service will become harder to maintain.
3. If readiness truth remains locally optimistic, operators and UI consumers will be misled.
4. If legacy scope is not removed aggressively enough, the repository will continue signaling the
   wrong ownership model.
5. If AI is introduced without strong guardrails, deterministic advisory truth could be weakened.

## Success Criteria

This RFC is successful when:

1. `lotus-advise` has a clear, defendable advisory-service boundary,
2. upstream and downstream ownership across Lotus apps is explicit and respected,
3. stateful and stateless advisory workflows fit one coherent operating model,
4. the repository, runtime, and persistence model are cleanly advisory-only,
5. the architecture is strong enough to support a bank-grade, marketable advisory product.
