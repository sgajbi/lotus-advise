# Repository Engineering Context

This file provides repository-local engineering context for `lotus-advise`.

For platform-wide truth, read:

1. `../lotus-platform/context/LOTUS-QUICKSTART-CONTEXT.md`
2. `../lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
3. `../lotus-platform/context/CONTEXT-REFERENCE-MAP.md`

## Repository Role

`lotus-advise` is the advisory workflow and proposal simulation service.

It owns advisor-led proposal lifecycle and recommendation-oriented execution readiness behavior.

## Business And Domain Responsibility

This repository owns:

1. advisor-led proposal simulation,
2. proposal lifecycle state,
3. advisory approvals and consent-related workflow behavior,
4. advisory execution readiness,
5. source-owned tactical house-view affected cohorts for bank-authored house-view instructions and
   caller-supplied source-backed candidate portfolios.

It does not own discretionary portfolio-management operations; those belong to `lotus-manage`.

## Current-State Summary

Current repository posture:

1. `lotus-advise` is now scoped to advisory-only workflows after the split from `lotus-manage`,
2. runtime smoke and production-profile guardrail validation are part of the real CI contract,
3. canonical upstream integration with `lotus-core` and `lotus-risk` matters for truthful proposal behavior,
4. proposal simulation, artifact, workspace, replay, and lifecycle surfaces now expose persisted backend-owned `proposal_decision_summary` and `proposal_alternatives`,
5. RFC-0023 advisor-review proposal narrative is supported in the proposal artifact,
   proposal-version review/replay, reviewed report-request package propagation, and downstream
   `lotus-report`/`lotus-render` advisor-use report rendering path, with `lotus-archive`
   support-safe archive metadata summaries for rendered advisor-use portfolio-review artifacts;
   `lotus-gateway` now exposes product-facing reviewed-narrative posture through canonical
   `lotus-advise` APIs and `lotus-workbench` renders the Gateway-backed advisor-use proposal
   narrative posture. `ProposalNarrativeEvidence:v1` is declared as a governed advisor-review
   evidence product with repo-native trust telemetry and `/platform/capabilities` reviewed
   narrative evidence feature/workflow promotion. Live runtime evidence now validates stateful
   advisor-review narrative requests, immutable read, non-persistent regeneration, advisor-use
   review, reviewed report-package request, replay evidence, deterministic guardrail-failure
   reproduction, and optional AI-assisted narrative validation when enabled. Canonical Workbench
   proof now covers `proposal.narrative_posture`. Slice 13/14 hardening records that even a clean
   advisor-review narrative release request cannot return `APPROVED_FOR_CLIENT_READY`.
   Client-ready commentary, compliance-review and client-draft narrative, and client communication
   remain gated. Standalone proposal-version
   narrative read and non-persistent regeneration APIs are supported for advisor-review posture.
   Historical Slice 0-11 audit wording is preserved only as audit context. Slice 12 closed the
   advisor-review Workbench canonical proof path and Slice 13/14 hardened the client-ready approval
   boundary; client-ready narrative, compliance-review narrative, client-draft narrative,
   client-ready publication, and external client communication remain gated future scope rather
   than supported RFC-0023 closure claims,
6. live operator evidence validates decision-summary and proposal-alternatives posture across canonical and degraded runtime paths,
7. upstream service consumption is classified under RFC-0082 in `docs/architecture/RFC-0082-upstream-contract-family-map.md`,
8. repo-native CI is already aligned to explicit lane expectations,
9. RFC-0086 repo-native declaration onboarding now covers the advisory proposal lifecycle product,
   proposal narrative evidence product, and a bounded tactical house-view affected-cohort product
   in `contracts/domain-data-products/`, with explicit upstream dependencies,
10. RFC-0087 trust telemetry proof for `AdvisoryProposalLifecycleRecord` and RFC-0023 trust
   telemetry proof for `ProposalNarrativeEvidence` now live under `contracts/trust-telemetry/`
   and are validated by `tests/unit/test_trust_telemetry.py` against the platform trust telemetry
   validator when `lotus-platform` is available,
11. the advisory workspace rationale path now uses the explicit `lotus-ai` workflow-pack execution
   seam for the `workspace_rationale.pack` family, preserves bounded run posture in the advisory
   response, and exposes a separate bounded review-action pass-through that retains Lotus AI
   lineage truth,
12. execution handoff, status, and delivery projections carry explicit ownership-boundary evidence
   so advisory posture cannot be confused with downstream execution system-of-record truth.

## Architecture And Module Map

Primary areas:

1. `src/`
   advisory APIs, workflow logic, and supporting modules.
2. `scripts/`
   dependency-health, runtime smoke, OpenAPI, vocabulary, and governance scripts.
3. `docs/`
   advisory standards and workflow documentation.
4. `tests/`
   unit, integration, and e2e validation.
5. `wiki/`
   canonical authored source for GitHub wiki publication and advisory operator onboarding summaries.
6. `contracts/domain-data-products/`
   repo-native producer and consumer declarations for governed advisory products and dependencies.
7. `contracts/trust-telemetry/`
   repo-native RFC-0087 trust telemetry fixtures for governed advisory products.

## Runtime And Integration Boundaries

Runtime model:

1. FastAPI advisory service,
2. depends on `lotus-core` and `lotus-risk`,
3. consumed through `lotus-gateway` for integrated product flows.

Boundary rules:

1. advisor-only workflows belong here,
2. management-only workflows belong in `lotus-manage`,
3. proposal simulation must remain aligned with authoritative upstream data and risk posture,
4. decision-summary, proposal-alternatives generation, ranking, selection, approval-requirement, and material-change semantics are backend-owned contracts and must not be generated, reranked, or re-inferred in UI or support layers,
5. proposal alternatives must remain anchored to canonical `lotus-core` simulation and `lotus-risk` enrichment rather than local duplicated calculations,
6. tactical house-view affected cohorts must remain bounded to supplied source-backed candidates,
   preserve source refs, and must not discover the global portfolio universe or open DPM campaigns,
7. execution handoff, status, and delivery surfaces must preserve the boundary that `lotus-advise`
   records advisory posture while downstream providers remain execution systems of record,
8. REST/OpenAPI remains the canonical integration contract; gRPC is not justified for current advisory upstream calls,
9. runtime smoke should honor injected CI DSNs and canonical service identities rather than stale local assumptions.

## Repo-Native Commands

Use these commands as the primary local contract:

1. install
   `make install`
2. fast local gate
   `make check`
3. PR-grade local gate
   `make ci`
4. feature-lane local gate
   `make ci-local`
5. Docker parity
   `make ci-local-docker`
6. run locally
   `make run`
7. repo-native domain product gate
   `make domain-data-products-gate`

## Validation And CI Expectations

`lotus-advise` uses explicit CI lanes:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

Important validation expectations:

1. dependency health, OpenAPI, vocabulary, and no-alias governance are active,
2. migration smoke, coverage, Docker build, Postgres runtime smoke, and production-profile guardrail validation are part of the merge gate,
3. advisory workflow changes should be validated against canonical upstream posture,
4. live runtime evidence should prove decision-summary and proposal-alternatives posture on canonical and degraded paths when advisory proposal behavior changes materially.

## Standards And RFCs That Govern This Repository

Most relevant current governance:

1. `../lotus-platform/rfcs/RFC-0066-lotus-advise-to-lotus-advise-and-lotus-manage-split.md`
2. `../lotus-platform/rfcs/RFC-0067-centralized-api-vocabulary-inventory-and-openapi-documentation-governance.md`
3. `../lotus-platform/rfcs/RFC-0072-platform-wide-multi-lane-ci-validation-and-release-governance.md`
4. `../lotus-platform/rfcs/RFC-0073-lotus-ecosystem-engineering-context-and-agent-guidance-system.md`
5. `../lotus-platform/rfcs/RFC-0082-lotus-core-domain-authority-and-analytics-serving-boundary-hardening.md`
6. `docs/architecture/RFC-0082-upstream-contract-family-map.md`
7. `docs/architecture/RFC-0086-repo-native-domain-product-onboarding.md`
8. `docs/standards/`

## Known Constraints And Implementation Notes

1. advisory and management boundaries must remain explicit after the repository split,
2. runtime smoke orchestration is operationally important here because CI includes real environment behavior, not just unit logic,
3. proposal behavior must not drift away from upstream data and risk authorities,
4. persisted proposal versions are expected to preserve the exact decision summary and proposal alternatives used by artifact, replay, workspace, and operator evidence surfaces,
5. proposal alternatives remain opt-in, bounded, and dependent on canonical upstream authorities; unsupported objectives must reject explicitly rather than degrade into guessed behavior,
6. restricted-product alternatives remain deferred until canonical eligibility evidence is available,
7. advisory stateful context operational reads, advisory simulation execution, and enrichment fallback labels remain RFC-0082 watchlist surfaces,
8. RFC-0086 consumer declarations should stay conservative and only reference upstream products
   already approved and truthfully mapped in the current platform catalog,
9. advisory lifecycle changes should update both code and repo context in the same slice,
10. tactical house-view cohort changes should preserve the Advise/Manage boundary: Advise owns
   source cohort evaluation; Manage owns DPM workflows, campaigns, policies, and evidence,
11. repo-local `wiki/` content should stay concise, operator-focused, and derived from repo truth rather
   than duplicating the full `docs/` tree.

## Context Maintenance Rule

Update this document when:

1. advisory workflow ownership or lifecycle scope changes,
2. repo-native commands or runtime smoke behavior changes,
3. upstream integration posture changes materially,
4. guardrail or production-profile expectations change,
5. RFC-0082 contract-family classification changes,
6. current-state rollout posture changes,
7. wiki ownership or publication workflow changes.

## Cross-Links

1. `../lotus-platform/context/LOTUS-QUICKSTART-CONTEXT.md`
2. `../lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
3. `../lotus-platform/context/CONTEXT-REFERENCE-MAP.md`
4. `../lotus-platform/context/Repository-Engineering-Context-Contract.md`
5. [Lotus Developer Onboarding](../lotus-platform/docs/onboarding/LOTUS-DEVELOPER-ONBOARDING.md)
6. [Lotus Agent Ramp-Up](../lotus-platform/docs/onboarding/LOTUS-AGENT-RAMP-UP.md)
