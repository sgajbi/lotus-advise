# RFC-0006A: Advisory-Only Architecture Reset and Integration Seams

- Status: IMPLEMENTED
- Created: 2026-03-25
- Depends On: RFC-0006
- Doc Location: `docs/rfcs/RFC-0006A-advisory-only-architecture-reset-and-integration-seams.md`

## 1. Executive Summary

This RFC is the first implementation slice under `RFC-0006`.

It establishes the minimum codebase and architecture reset required before deeper advisory feature
delivery:

1. remove stale legacy runtime remnants from `lotus-advise`,
2. make repository and runtime ownership explicitly advisory-only,
3. introduce integration seams for `lotus-core`, `lotus-risk`, `lotus-report`, `lotus-ai`, and
   optional `lotus-performance`,
4. create the foundation for dependency-aware capability reporting,
5. align the repository with `lotus-platform` vocabulary and documentation governance.

This RFC does not yet deliver stateful portfolio sourcing or `lotus-core` simulation reuse.
Instead, it prepares the repository so those follow-on RFCs can be implemented cleanly.

Implementation intent for this slice:

- perform only the advisory-only architecture reset,
- do not yet change the authoritative simulation or risk source of truth,
- do not yet redesign external advisory request contracts beyond what is needed for seam creation.

## 2. Problem Statement

`lotus-advise` still contains structural traces of an older repository shape where advisory scope
was not clearly separated from legacy runtime concerns.

Current issues include:

1. stale legacy runtime remnants remain in the repository,
2. documentation still describes mixed or outdated architecture ownership,
3. integration boundaries are not yet expressed through clear adapter seams,
4. capability reporting is still local-flag-centric rather than dependency-aware,
5. the repository shape does not yet make the target advisory-only ownership model obvious.

If we skip this reset and go straight into new advisory features, we will compound architectural
drift and make later service-boundary cleanup harder.

## 3. Goals and Non-Goals

### 3.1 Goals

1. remove stale active-runtime traces of legacy non-advisory scope from `lotus-advise`,
2. make advisory-only ownership clear in docs, module structure, and runtime language,
3. establish explicit integration seam modules for upstream and downstream dependencies,
4. prepare capability/readiness surfaces for dependency-aware truth,
5. align this foundation slice with `lotus-platform` vocabulary and API documentation standards.

### 3.2 Non-Goals

This RFC does not:

1. introduce `stateful` and `stateless` request contracts,
2. switch advisory simulation to `lotus-core`,
3. integrate live risk enrichment from `lotus-risk`,
4. implement AI workflows,
5. implement advisory workspace mutation APIs,
6. deliver execution integration.

Those are follow-on lettered RFCs under the `RFC-0006` program.

## 4. Proposed Design

### 4.1 Advisory-Only Repository Reset

`lotus-advise` must present itself as an advisory-only service.

Implementation direction:

1. remove stale legacy source-layout remnants that no longer represent active ownership,
2. remove tracked bytecode artifacts and other stale runtime leftovers,
3. update repository docs so they no longer describe `lotus-advise` as anything other than an
   advisory service,
4. preserve historical references only where needed for migration traceability.

### 4.2 Integration Seam Modules

Introduce explicit integration seams even if early implementations are stubs or no-op adapters.

Required integration seam families:

1. `lotus_core`
   - portfolio sourcing adapter
   - simulation adapter
2. `lotus_risk`
   - proposal risk-enrichment adapter
3. `lotus_report`
   - report request adapter
4. `lotus_ai`
   - advisory AI task adapter
5. optional `lotus_performance`
   - analytics context adapter

Rules:

1. domain ownership stays outside `lotus-advise`,
2. adapters may orchestrate and normalize responses,
3. adapters must not re-implement upstream domain logic.

### 4.3 Capability and Readiness Foundation

The first implementation step for capability surfaces is to separate local feature toggles from
dependency-aware readiness.

The capability model should begin evolving toward:

1. `feature_enabled`
2. `operational_ready`
3. `dependency_status`
4. `fallback_mode`
5. `degraded_reason`

This RFC does not require all capability responses to be fully redesigned, but it does require the
codebase to create a clear seam where dependency-aware truth can be added without breaking the
service boundary model.

### 4.4 Platform Governance Alignment

This implementation slice must align with `lotus-platform` governance.

Required alignment:

1. canonical domain vocabulary from `lotus-platform`,
2. RFC-0067-style OpenAPI and API vocabulary discipline,
3. full request/response documentation with descriptions and examples for any new or changed APIs,
4. Lotus-branded API descriptions and examples,
5. no local aliases when canonical platform terms already exist.

### 4.5 Transitional Compatibility

This RFC allows temporary compatibility bridges where needed, provided they do not blur long-term
ownership.

Allowed temporarily:

1. existing advisory simulation flows may remain while future `lotus-core` integration is
   designed,
2. existing lifecycle APIs may remain while architecture seams are introduced.

Not allowed:

1. expanding stale legacy non-advisory ownership inside `lotus-advise`,
2. introducing new service-local vocabulary that conflicts with `lotus-platform`,
3. adding new advisory features directly on top of ambiguous DPM-era structure.

## 5. Concrete Scope

This RFC should produce the following Slice 1 repository changes:

1. remove stale legacy runtime remnants from active source layout,
2. update project/docs language to advisory-only ownership,
3. introduce initial integration adapter package structure,
4. introduce dependency-readiness helper structure or service seam,
5. update review artifacts and architecture docs where needed to reflect the new baseline.

Illustrative package direction:

1. `src/integrations/lotus_core/`
2. `src/integrations/lotus_risk/`
3. `src/integrations/lotus_report/`
4. `src/integrations/lotus_ai/`
5. `src/integrations/lotus_performance/`
6. `src/api/capabilities/` or equivalent readiness-focused module seam

Exact file layout can adapt to repository conventions, but the seam responsibilities must be clear.

Slice 1 boundary:

1. repository cleanup and seam scaffolding are in scope,
2. active architecture and repository-overview docs are in scope,
3. historical RFCs, ADRs, demo packs, and migration evidence may remain unchanged where they serve
   archival traceability during this slice,
4. behavior-preserving refactors are allowed,
5. major feature behavior changes are out of scope.

## 6. Test Plan

This RFC should be considered complete only when the following are covered:

1. unit tests confirm stale runtime selections or imports are removed where applicable,
2. unit tests validate integration seam construction and contract boundaries,
3. docs and OpenAPI-related tests continue to pass,
4. repository searches confirm stale legacy runtime paths are removed from active architecture
   docs,
5. lint, type, and test gates remain green.

## 7. Rollout and Compatibility

Rollout approach:

1. land architecture reset and seam creation first,
2. keep existing advisory flows working,
3. use later `RFC-0006` lettered RFCs to migrate actual behavior onto the new seams.

Compatibility expectation:

- additive and cleanup-oriented,
- no immediate client-facing contract break is required in this slice,
- but stale internal ownership signals must be removed.

## 8. Status and Reason Code Conventions

This RFC introduces no new top-level domain statuses.

It also introduces no new advisory reason codes.

Any diagnostics added during implementation must:

1. use upper snake case,
2. distinguish architecture/readiness conditions from domain-evaluation outcomes,
3. remain compatible with platform vocabulary standards.

## 9. Acceptance Criteria

This RFC is complete when:

1. `lotus-advise` no longer contains stale active legacy runtime remnants,
2. advisory-only ownership is clear in repository docs and architecture language,
3. integration seam packages or equivalent adapter boundaries exist,
4. dependency-aware capability/readiness work has an explicit implementation seam,
5. new or changed APIs remain fully documented and Lotus-branded,
6. all changes align with `lotus-platform` standards and canonical vocabulary.

For Slice 1 sign-off, "active" means:

1. current source layout,
2. current runtime wiring,
3. primary architecture and repository-overview docs,
4. newly introduced scaffolding for follow-on slices.

It does not require rewriting all historical references preserved in archival RFC, ADR, demo, or
migration evidence documents during this slice.

## 10. Follow-On RFCs

Recommended next RFCs after this slice:

1. `RFC-0006B`: advisory `stateless` and `stateful` operating mode contract
2. `RFC-0006C`: `lotus-core` simulation integration and de-duplication
3. `RFC-0006D`: `lotus-risk` enrichment integration
4. `RFC-0006E`: advisory workspace APIs
5. `RFC-0006F`: AI-native advisory workflows through `lotus-ai`

