# RFC-0006: lotus-advise Target Operating Model and Integration Architecture

- Status: PROPOSED
- Created: 2026-03-25
- Depends On: RFC-0014G, RFC-0003, RFC-0004
- Doc Location: `docs/rfcs/RFC-0006-lotus-advise-target-operating-model-and-integration-architecture.md`

## 1. Executive Summary

`lotus-advise` should become the advisory workflow and orchestration service for the Lotus estate,
not a second portfolio simulation or risk-calculation engine.

This RFC resets the service boundary around that principle and defines the first-order architecture:

1. `lotus-advise` owns advisory workspace, proposal lifecycle, approvals, consent, and execution
   handoff orchestration.
2. `lotus-core` remains the authoritative owner of canonical portfolio state and portfolio
   simulation.
3. `lotus-risk` owns risk calculations and risk analytics consumed by advisory workflows.
4. `lotus-report` owns portfolio review and report payload generation.
5. `lotus-ai` provides governed AI infrastructure for advisor-assistive features.
6. `lotus-advise` must support both `stateless` and `stateful` operating modes.
7. Stale legacy runtime elements that no longer belong to advisory must be removed from
   `lotus-advise`.
8. Common vocabulary and engineering standards must remain governed centrally by
   `lotus-platform`, not reinvented locally in `lotus-advise`.

This RFC is the architecture foundation for subsequent implementation RFCs. It defines what
`lotus-advise` is, what it is not, how it fits into the platform, and which seams must exist before
we add interactive workspace, AI-native features, or scaled production rollout.

This RFC also establishes that cross-application vocabulary, API naming, OpenAPI documentation
quality, and other shared standards are governed by `lotus-platform` and must be consumed by
`lotus-advise` as platform rules rather than redefined in service-local conventions.

## 2. Problem Statement

The current `lotus-advise` repository contains a valuable advisory proposal engine and workflow
surface, but its architecture still reflects an earlier combined repository shape with legacy
runtime and documentation drift.

This creates five core problems:

1. ownership boundaries are blurred, especially around simulation and older DPM-aligned concepts,
2. real advisory workflows are not yet centered on stateful portfolio sourcing from `lotus-core`,
3. risk and reporting responsibilities are not yet enforced as external service boundaries,
4. AI opportunities are not yet framed as governed cross-service capabilities through `lotus-ai`,
5. stale legacy artifacts and naming continue to signal scope that no longer belongs in this
   service.

If this is not corrected now, `lotus-advise` risks becoming:

- an orchestration service with hidden duplicate domain logic,
- a simulation surface that cannot scale cleanly across the platform,
- a service that competes with `lotus-core`, `lotus-risk`, and `lotus-report` instead of composing
  them.

## 3. Goals

This RFC has the following goals:

1. define the authoritative service boundary for `lotus-advise`,
2. establish the upstream and downstream integration model across Lotus services,
3. standardize `stateless` and `stateful` advisory operating modes,
4. define the role of `lotus-ai` in advisory workflows,
5. define the cleanup direction for stale legacy scope and code,
6. anchor `lotus-advise` to Lotus-wide vocabulary and standards governed by `lotus-platform`,
7. provide the architecture baseline for follow-on RFCs.

## 4. Non-Goals

This RFC does not:

1. implement interactive workspace APIs,
2. define the final AI feature payload schemas,
3. define broker/OMS connector details,
4. replace existing advisory proposal lifecycle APIs immediately,
5. move database tables or rewrite historical artifacts in this document,
6. force `lotus-performance` integration in v1 if no advisory workflow needs it yet.

Those concerns should be addressed by follow-on RFCs that build on this architecture baseline.

## 5. Platform Governance Baseline

`lotus-advise` must conform to cross-application governance defined in `lotus-platform`.

This includes, at minimum:

1. canonical domain vocabulary,
2. cross-app API naming rules,
3. OpenAPI quality requirements,
4. API vocabulary inventory governance,
5. dependency hygiene and security standards,
6. migration, durability, testing, and enterprise-readiness standards where applicable.

The governing source for shared vocabulary and standards is `lotus-platform`, including:

1. `RFC-0003: Canonical Domain Vocabulary`,
2. `RFC-0067: Centralized API Vocabulary Inventory and OpenAPI Documentation Governance`,
3. platform standards documents such as domain vocabulary, migration, durability, observability,
   and testing standards.

Rule:

- `lotus-advise` may define advisory-specific concepts,
- but it must not invent alternative names for platform-wide concepts that already have a canonical
  Lotus term.

## 6. Proposed Operating Model

### 5.1 Service Mission

`lotus-advise` is the advisory workflow service for:

1. advisor proposal drafting,
2. proposal evaluation orchestration,
3. workflow gates and review routing,
4. proposal versioning, approvals, and client consent,
5. execution handoff readiness and execution-state aggregation,
6. explainability assembly for advisor and reviewer workflows.

`lotus-advise` is not the system of record for portfolio data, not the owner of core portfolio
simulation, not the owner of risk analytics, and not the owner of reporting outputs.

### 5.2 Service Ownership Boundaries

`lotus-advise` owns:

1. advisory workspace sessions and draft mutations,
2. proposal drafts, immutable proposal versions, and lifecycle transitions,
3. workflow decisions that combine upstream portfolio, risk, and policy evidence into advisory
   next-step outcomes,
4. orchestration of upstream service calls needed for proposal evaluation,
5. advisor/reviewer-facing explanation assembly,
6. execution handoff requests and execution audit correlation for advisory proposals.

`lotus-advise` does not own:

1. canonical portfolio positions, transactions, cash ledgers, valuations, or benchmark source data,
2. authoritative portfolio simulation math if already provided by `lotus-core`,
3. risk calculations that belong in `lotus-risk`,
4. report-generation payload ownership that belongs in `lotus-report`,
5. shared AI runtime, provider, retrieval, prompt, or safety infrastructure that belongs in
   `lotus-ai`.

## 7. Platform Integration Boundaries

### 6.1 lotus-core

`lotus-core` is the authoritative dependency for:

1. canonical portfolio snapshot assembly,
2. current holdings, transactions, cash, valuation, and benchmark context,
3. stateful portfolio sourcing by `portfolio_id` and `as_of`,
4. canonical portfolio simulation capability for advisory before/after state evaluation.

`lotus-advise` must reuse `lotus-core` portfolio simulation capability rather than maintain a
long-term duplicate portfolio simulation engine.

Short-term note:

- existing deterministic advisory simulation behavior may remain as a transitional compatibility
  path while `lotus-core` integration is introduced,
- but the target architecture is clear: `lotus-core` owns the canonical simulation contract.

### 6.2 lotus-risk

`lotus-risk` owns all risk-related calculations consumed by advisory workflows, including but not
limited to:

1. concentration and issuer exposure,
2. factor and scenario exposures,
3. stress and risk-limit checks,
4. pre-trade and post-simulation risk analytics,
5. risk deltas between before and after portfolio states.

`lotus-advise` may orchestrate, display, and route risk outcomes, but it must not become a second
risk engine.

### 6.3 lotus-report

`lotus-report` owns portfolio review and reporting payload generation.

`lotus-advise` may request reporting artifacts or assemble workflow references to them, but
portfolio review report ownership stays in `lotus-report`.

### 6.4 lotus-performance

`lotus-performance` is optional for the first advisory architecture slice.

It should be integrated only where advisory workflows clearly benefit from:

1. return context,
2. benchmark-relative context,
3. contribution or attribution context,
4. proposal comparison across performance-oriented analytics dimensions.

This RFC intentionally leaves `lotus-performance` as an optional but architecturally supported seam.

### 6.5 lotus-ai

`lotus-ai` is a strategic dependency for governed AI-native advisory workflows.

`lotus-advise` remains the domain owner, while `lotus-ai` supplies:

1. task execution runtime,
2. prompt and rollout governance,
3. retrieval and grounding infrastructure,
4. safety controls,
5. audit and observability for AI actions.

## 8. Advisory Operating Modes

`lotus-advise` must support two explicit operating modes.

### 7.1 Stateless Mode

Purpose:

- deterministic replay,
- partner integration,
- testability,
- sandbox and what-if exploration.

In `stateless` mode, the caller provides the advisory evaluation inputs directly in the request.

Examples:

1. portfolio snapshot,
2. market-data snapshot,
3. restrictions or shelf metadata,
4. proposal deltas,
5. optional reference model or benchmark context.

### 7.2 Stateful Mode

Purpose:

- production advisory workflows,
- UI-driven advisor experience,
- live portfolio review and proposal creation from Lotus system-of-record data.

In `stateful` mode, `lotus-advise` receives identity and selection inputs, then resolves canonical
state through upstream services, especially `lotus-core`.

Examples:

1. `portfolio_id`,
2. `household_id` when supported,
3. `as_of`,
4. proposal deltas or intent overrides,
5. optional mandate, benchmark, policy pack, or scenario inputs.

### 7.3 Required Contract Direction

All new advisory evaluation RFCs must converge on:

1. `input_mode: "stateless" | "stateful"`,
2. `stateless_input` for direct payload sourcing,
3. `stateful_input` for Lotus-sourced portfolio resolution,
4. explicit `resolved_context` in responses for replayability and audit,
5. stable lineage references to upstream snapshot identifiers and dependency versions.

## 9. AI-Driven Advisory Opportunities

AI in `lotus-advise` must be advisor-assistive, evidence-grounded, and operationally governed.

The target AI feature families are:

1. proposal rationale generation from deterministic upstream evidence,
2. meeting-prep summaries for advisors and relationship managers,
3. note-to-proposal drafting from structured or semi-structured advisor notes,
4. policy and exception explanation in plain language,
5. client communication drafting grounded in approved proposal facts,
6. scenario exploration assistance that maps natural language to deterministic advisory actions,
7. reviewer copilot workflows for risk and compliance review.

Guardrail:

- AI must not silently replace deterministic portfolio, risk, or workflow truth,
- all AI outputs used in workflow decisions must retain evidence references,
- final domain decisions remain grounded in deterministic service outputs and policy gates.

## 10. Vocabulary and Contract Governance

All new `lotus-advise` contracts introduced under this architecture must align to `lotus-platform`
governance.

Required contract rules:

1. use Lotus canonical snake_case field names,
2. use Lotus canonical headers such as `X-Correlation-Id` and `Idempotency-Key`,
3. reject aliases when a canonical term already exists,
4. use shared business-meaningful identifiers such as `portfolio_id`, `client_id`, `proposal_id`,
   `proposal_version_no`, and `correlation_id`,
5. document attributes through the platform-governed vocabulary inventory model rather than through
   disconnected local descriptions,
6. keep OpenAPI documentation compliant with platform quality gates,
7. present Lotus-branded API documentation and examples suitable for external and internal platform
   consumers.

Examples of implications for `lotus-advise`:

1. `stateful_input` must use canonical identity fields already governed at platform level,
2. advisory lifecycle and workspace contracts must not introduce local aliases for existing
   portfolio, client, proposal, or calculation concepts,
3. any AI workflow contract must use platform-governed naming and evidence identifiers,
4. service-local convenience naming that conflicts with `lotus-platform` is forbidden.

### 10.1 API Documentation Standard

All `lotus-advise` APIs implemented under this architecture must be fully documented in a
Lotus-branded way.

Minimum documentation requirements for every API operation:

1. `summary`,
2. `description`,
3. tags,
4. success response documentation,
5. error response documentation,
6. Lotus-branded examples that reflect real advisory workflows and Lotus terminology.

Minimum documentation requirements for every request and response field:

1. field name,
2. type,
3. description,
4. example.

Minimum documentation requirements for every request and response schema:

1. schema-level purpose,
2. request example,
3. response example,
4. documented required versus optional fields,
5. linkage to canonical vocabulary inventory entries where applicable.

Documentation rules:

1. examples must be business-meaningful, not placeholder-only,
2. descriptions must explain domain intent, not only implementation mechanics,
3. request and response examples must use Lotus terminology and realistic advisory scenarios,
4. OpenAPI must remain consistent with code and generated vocabulary inventory artifacts,
5. platform conformance gates should fail if required descriptions or examples are missing.

Lotus branding expectation:

1. the API surface should present itself as part of the Lotus platform,
2. examples and descriptions should refer to Lotus advisory workflows, Lotus identifiers, and Lotus
   service interactions where appropriate,
3. generic or vendor-template wording should be avoided when a Lotus-specific domain description is
   available.

## 11. Target Microservice Architecture

### 9.1 Internal Modules

The target internal architecture for `lotus-advise` should include:

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
   - `lotus-core` adapter
   - `lotus-risk` adapter
   - `lotus-report` adapter
   - optional `lotus-performance` adapter
   - `lotus-ai` adapter
   - execution adapter seam
4. `capability_and_readiness`
   - dependency-aware capability truth
   - degraded-mode diagnostics
5. `execution_handoff`
   - proposal-to-execution request lifecycle
   - execution-state aggregation
6. `explainability`
   - advisor and reviewer explanation assembly

### 9.2 Scalability Principles

`lotus-advise` must be designed for:

1. stateless API horizontal scaling for evaluation requests,
2. async job offload for heavier multi-service orchestration,
3. replay-safe request and workspace mutation persistence,
4. explicit dependency timeouts and degradation handling,
5. no shared-database coupling with other services,
6. append-only or immutable records for critical lifecycle and audit paths,
7. capability reporting that reflects operational dependency truth, not only local feature flags.

## 12. Cleanup of Legacy Advisory-External Scope

The repository must remove stale legacy scope that no longer belongs in `lotus-advise`.

This includes:

1. removing stale legacy runtime remnants,
2. removing or rewriting documentation that still presents `lotus-advise` as anything other than
   an advisory service,
3. renaming APIs, docs, and modules where needed to reflect advisory-only ownership,
4. preserving historical artifacts only where required for traceability, not as active runtime
   structure.

Follow-on RFCs should identify the exact migration slices for these removals.

## 13. Capability and Readiness Model

The current local-feature-flag capability model is insufficient for the target platform posture.

`lotus-advise` must evolve toward a capability contract that distinguishes:

1. `feature_enabled`
2. `operational_ready`
3. `degraded`
4. `dependency_requirements`
5. `dependency_status`
6. `fallback_mode`

Examples:

1. advisory workspace may be enabled while stateful portfolio sourcing is degraded,
2. proposal lifecycle may be enabled while risk enrichment is unavailable,
3. AI drafting may be enabled only for allowlisted tenants or workflows.

## 14. Phased Implementation Plan

### Phase 1: Architecture Reset

1. approve this RFC,
2. remove stale DPM scope markers and repo leftovers,
3. introduce explicit advisory-only architecture language,
4. align service docs and contracts to `lotus-platform` vocabulary and standards,
5. define adapter seams for `lotus-core`, `lotus-risk`, `lotus-report`, optional
   `lotus-performance`, and `lotus-ai`.

### Phase 2: Operating Mode Contract

1. introduce `input_mode`,
2. add `stateless_input` and `stateful_input`,
3. add `resolved_context`,
4. support stateful sourcing from `lotus-core`,
5. add platform-governed OpenAPI and API-vocabulary conformance for new advisory contracts,
6. ensure every new request and response schema includes descriptions, types, and Lotus-branded
   examples.

### Phase 3: Upstream Authority Realignment

1. route portfolio simulation through `lotus-core`,
2. route risk analytics through `lotus-risk`,
3. remove duplicated long-term simulation and risk ownership from `lotus-advise`.

### Phase 4: Advisory Workspace and AI

1. implement iterative workspace contracts,
2. add AI-assisted but evidence-grounded advisor workflows through `lotus-ai`,
3. add dependency-aware capability and degraded-mode reporting.

### Phase 5: Reporting and Execution Completion

1. integrate `lotus-report` review/report payloads,
2. implement execution handoff and execution-state lifecycle,
3. expand production-readiness and observability posture.

## 15. Test Plan

This RFC requires follow-on implementation RFCs to include:

1. unit tests for mode resolution and adapter orchestration,
2. integration tests against `lotus-core` stateful sourcing,
3. integration tests against `lotus-risk` risk-enrichment paths,
4. integration tests for capability/readiness truth under dependency degradation,
5. end-to-end tests through `lotus-gateway` and `lotus-workbench`,
6. audit and replay validation for both `stateless` and `stateful` modes,
7. OpenAPI and API vocabulary conformance validation against `lotus-platform` governance,
8. schema and operation documentation validation for descriptions, examples, and Lotus branding
   quality.

## 16. Rollout and Compatibility

Compatibility expectations:

1. existing advisory lifecycle APIs may remain during migration,
2. new mode-aware APIs may coexist with transitional contracts temporarily,
3. duplication in simulation or risk logic is tolerated only as a temporary compatibility bridge,
4. long-term authority must converge to the ownership boundaries defined here.

## 17. Status and Reason Code Conventions

This RFC does not introduce new top-level domain statuses.

All follow-on RFCs must preserve:

1. `READY`
2. `PENDING_REVIEW`
3. `BLOCKED`

Any new advisory diagnostics must:

1. use upper snake case reason codes,
2. distinguish dependency failures from domain rule failures,
3. identify whether fallback, degraded, or blocking behavior was applied.

## 18. Open Questions

1. whether `lotus-core` portfolio simulation should be consumed synchronously for small requests and
   asynchronously for larger requests,
2. which advisory workflows should require `lotus-performance` in the first commercial release,
3. whether execution-state tracking remains inside `lotus-advise` or should later split into a
   dedicated execution service,
4. whether household-level advisory context is introduced in the first stateful slice or later.

## 19. Follow-On RFCs Required

This RFC should be followed by at least:

1. an RFC for `stateless` and `stateful` advisory contract implementation,
2. an RFC for `lotus-core` simulation integration and local simulation de-duplication,
3. an RFC for `lotus-risk` risk-enrichment integration,
4. an RFC for advisory workspace APIs,
5. an RFC for AI-native advisory workflows through `lotus-ai`,
6. an RFC for legacy advisory-external cleanup and repository restructuring,
7. an RFC or implementation slice for full `lotus-platform` vocabulary and standards conformance in
   `lotus-advise`.

