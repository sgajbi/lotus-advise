# RFC-0022: Proposal Alternatives and Portfolio Construction Workbench

- Status: DRAFT
- Created: 2026-04-12
- Owners: lotus-advise
- Requires Approval From: lotus-advise, lotus-core, lotus-risk, lotus-manage maintainers
- Depends On: RFC-0006, RFC-0007, RFC-0008, RFC-0009, RFC-0010, RFC-0013, RFC-0016, RFC-0019, RFC-0020, RFC-0021
- Related Platform Guidance: `lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
- Related Platform Governance: `lotus-platform/rfcs/RFC-0072-platform-wide-multi-lane-ci-validation-and-release-governance.md`

## Executive Summary

`lotus-advise` can simulate and persist a proposal, but a business-grade advisory platform must help an advisor compare credible alternatives, not only inspect one manually constructed trade list.

This RFC defines an in-place enhancement to existing advisory proposal APIs that introduces deterministic proposal alternatives and portfolio construction support. The goal is to let an advisor evaluate multiple feasible paths such as reduce concentration, raise cash, improve currency alignment, lower risk review burden, rebalance toward a reference model, or produce a lower-cost execution path.

The capability must remain banking-grade:

1. alternatives are generated from explicit advisor objectives and constraints,
2. all portfolio, AUM, valuation, allocation, cash, and simulation calculations remain delegated to `lotus-core`,
3. all risk calculations remain delegated to `lotus-risk`,
4. suitability and decision posture are delegated to RFC-0021 decision-summary policy,
5. no UI surface invents an alternative that cannot be reproduced by backend evidence,
6. every alternative is auditable, replayable, and explainable.

Because `lotus-advise` is not live and callers are controlled, this RFC enhances existing APIs in place. It does not introduce public `/v2` APIs or duplicate simulation contracts.

## Why This RFC Exists

Private-banking advisory work is rarely a single-path problem. A client, relationship manager, investment counsellor, and risk reviewer often need to compare alternatives:

1. the advisor's original recommendation,
2. a less risky path,
3. a lower-turnover path,
4. a mandate-aligned rebalance,
5. a concentration-remediation path,
6. a cash-raising path,
7. a proposal that avoids restricted products,
8. a proposal with fewer approval requirements.

Without a backend-owned alternatives capability, the UI will eventually add superficial comparison widgets over manually prepared payloads. That would not be enterprise grade because it would lack deterministic generation, reproducible evidence, policy traceability, and canonical calculation parity.

This RFC makes alternatives a backend-governed advisory capability while preserving clear domain authority boundaries.

## Current State

### What Is Already Strong

Current proposal capability already provides:

1. canonical stateful portfolio simulation through `lotus-core`,
2. before/after allocation and AUM evidence,
3. concentration risk lens through `lotus-risk`,
4. suitability output, workflow gate semantics, and proposal status,
5. proposal persistence, versioning, async operation replay, workspace save/handoff, artifact generation, and delivery evidence,
6. RFC-0021 target decision summary and enterprise suitability policy.

### What Is Not Yet Business Grade

Current proposal capability does not yet provide:

1. backend-generated proposal alternatives,
2. advisor objective modeling for alternative construction,
3. scenario constraints such as turnover, cash floor, product shelf, tax-sensitive holding, or concentration target,
4. deterministic ranking of alternatives,
5. side-by-side comparison evidence that is consistent across API, UI, artifact, and replay,
6. rejection reasons for alternatives that cannot be generated,
7. auditable linkage between each alternative and its construction objective.

## Problem Statement

`lotus-advise` needs to become the advisory orchestration authority for comparing proposal alternatives without becoming a portfolio optimizer, valuation engine, risk engine, or execution engine.

The platform needs a reusable construction layer that can:

1. accept explicit construction objectives and constraints,
2. produce candidate trade intents or cash-flow adjustments,
3. submit each candidate to canonical `lotus-core` simulation,
4. request canonical risk evidence from `lotus-risk`,
5. apply RFC-0021 decision summary and suitability posture,
6. rank and explain alternatives using deterministic advisory criteria,
7. persist and replay the full alternatives evidence.

A banking-grade platform must never present an alternative as recommended unless its construction logic, calculation evidence, suitability posture, risks, constraints, and approval implications are explicit.

## Requirement Traceability

| Requirement | RFC Section | Acceptance Evidence Required |
| --- | --- | --- |
| Alternatives must be backend-owned | Target API Contract, API and UI Alignment | API, artifact, and workspace tests prove alternatives are returned from backend evidence |
| Canonical calculations must remain in upstream services | Domain Authority Boundaries | Tests prove alternatives call `lotus-core` for simulation and do not recalculate AUM/allocation locally |
| Risk lens must remain authoritative in `lotus-risk` | Domain Authority Boundaries | Integration tests compare alternative risk evidence to direct risk-service output |
| Alternatives must include rejected candidates | Rejected Alternative Model | Tests prove infeasible candidates return reason codes rather than disappearing silently |
| Ranking must be deterministic | Alternative Ranking Model | Pure ranking tests cover tie-breakers and policy precedence |
| UI must not invent comparison logic | API and UI Alignment | Contract exposes comparison and ranking fields needed by UI |
| Final documentation and agent guidance must be assessed | Slice 8 | Final slice evidence records context updates or explicit no-change decision |

## Goals

1. Add backend-governed proposal alternatives to existing proposal surfaces.
2. Model advisor construction objectives and constraints explicitly.
3. Generate alternatives through small, deterministic construction strategies, not opaque magic.
4. Use `lotus-core` for every candidate simulation.
5. Use `lotus-risk` for every candidate risk lens when risk evidence is required.
6. Use RFC-0021 decision summaries for every generated alternative.
7. Rank alternatives deterministically using business-relevant criteria.
8. Persist accepted and rejected alternative evidence with proposal versions and workspace state.
9. Make side-by-side comparison directly consumable by UI and artifacts.
10. Keep the architecture modular so new construction strategies can be added without route rewrites.

## Non-Goals

1. Do not introduce public `/v2` route families.
2. Do not build a black-box optimizer.
3. Do not replace portfolio managers or investment counsellors with automatic discretionary execution.
4. Do not let AI generate trades without deterministic constraints and backend validation.
5. Do not calculate AUM, allocation, valuation, cash, or risk locally in `lotus-advise`.
6. Do not support unrestricted security selection across the full market in the first implementation.
7. Do not create client-ready recommendation text. Narrative belongs to RFC-0023.
8. Do not bypass suitability, mandate, jurisdiction, product eligibility, or approval policy.

## Pre-Live Contract Hardening Decision

Because the app is not live, this RFC enhances existing contracts in place.

Allowed changes:

1. additive fields on proposal simulation, create, version, workspace, artifact, and replay responses,
2. new internal model names for construction objectives, constraints, alternatives, rankings, and rejection reasons,
3. optional read-only endpoints under existing `/advisory/proposals/...` route family,
4. internal construction-policy versions and ranking-policy versions.

Disallowed changes:

1. public `/v2` APIs,
2. duplicate simulation request/response families,
3. UI-only alternatives,
4. route-local optimization logic,
5. hidden changes to top-level status vocabulary.

## Domain Authority Boundaries

### lotus-core

`lotus-core` remains authoritative for:

1. portfolio state,
2. positions,
3. cash,
4. AUM,
5. valuation,
6. allocation,
7. market/reference data,
8. proposal simulation,
9. tradability and canonical portfolio math where available.

Every generated candidate must be simulated by `lotus-core` before it can be considered a valid alternative.

### lotus-risk

`lotus-risk` remains authoritative for:

1. concentration analytics,
2. risk lens calculations,
3. stress, factor, liquidity, credit, duration, and future risk methodologies when available,
4. risk lineage and methodology versions.

`lotus-advise` may compare and rank risk evidence, but must not calculate risk metrics locally.

### lotus-manage or Client/Mandate Authority

Client, mandate, booking center, advisory agreement, risk profile, restrictions, and preferences must come from canonical client/mandate sources when available.

If required client or mandate evidence is unavailable, alternative generation must degrade explicitly and must not claim mandate alignment.

### lotus-advise

`lotus-advise` owns:

1. advisory construction objectives,
2. construction strategy orchestration,
3. candidate trade intent generation within governed constraints,
4. alternative comparison and ranking policy,
5. rejected alternative reason codes,
6. persistence and replay of advisory alternatives evidence,
7. UI-ready comparison projection.

## Target Capability

The target capability introduces a `proposal_alternatives` evidence object with these layers:

1. construction request normalization,
2. objective and constraint validation,
3. candidate generation,
4. canonical simulation and risk enrichment,
5. decision summary projection,
6. alternative ranking,
7. comparison projection,
8. persistence and replay.

Each layer must be separately testable and reusable across simulate, create, version, workspace, artifact, and replay paths.

## Target API Contract

### Additive Request Fields

Existing proposal simulation/create/version/workspace requests may include an optional alternatives block:

```json
{
  "alternatives_request": {
    "enabled": true,
    "objectives": ["REDUCE_CONCENTRATION", "LOWER_TURNOVER"],
    "max_alternatives": 3,
    "constraints": {
      "cash_floor": {"amount": "25000", "currency": "USD"},
      "max_turnover_pct": "12.50",
      "preserve_holdings": ["ISIN:US0378331005"],
      "restricted_instruments": ["ISIN:US5949181045"],
      "allow_fx": true
    },
    "ranking_policy_id": "advisory-alternative-ranking.2026-04"
  }
}
```

### Additive Response Fields

Add `proposal_alternatives` wherever proposal evidence is available and alternatives were requested or persisted:

1. `POST /advisory/proposals/simulate`,
2. `POST /advisory/proposals`,
3. `POST /advisory/proposals/{proposal_id}/versions`,
4. async operation replay after success,
5. workspace evaluate/save/handoff,
6. proposal artifact generation,
7. proposal detail/version detail,
8. replay evidence.

### Optional Projection Endpoint

Add a read-only endpoint only if UI or artifact flows need a direct persisted projection:

1. `GET /advisory/proposals/{proposal_id}/versions/{version_id}/alternatives`

This endpoint must read persisted evidence. It must not silently recompute alternatives against newer data.

## Alternatives Request Model

Suggested fields:

1. `enabled`,
2. `objectives`,
3. `constraints`,
4. `max_alternatives`,
5. `candidate_generation_policy_id`,
6. `ranking_policy_id`,
7. `include_rejected_candidates`,
8. `evidence_requirements`.

## Construction Objective Vocabulary

Allowed initial objectives:

1. `REDUCE_CONCENTRATION`
2. `IMPROVE_RISK_ALIGNMENT`
3. `RAISE_CASH`
4. `LOWER_TURNOVER`
5. `IMPROVE_CURRENCY_ALIGNMENT`
6. `REBALANCE_TO_REFERENCE_MODEL`
7. `AVOID_RESTRICTED_PRODUCTS`
8. `MINIMIZE_APPROVAL_REQUIREMENTS`
9. `PRESERVE_CLIENT_PREFERENCES`
10. `LOWER_COST_AND_FRICTION`

Objectives must be explicit. The backend must not infer hidden objectives from UI labels.

## Constraint Model

Initial constraints should support:

1. `cash_floor`,
2. `max_turnover_pct`,
3. `max_trade_count`,
4. `min_trade_amount`,
5. `preserve_holdings`,
6. `restricted_instruments`,
7. `do_not_buy`,
8. `do_not_sell`,
9. `allow_fx`,
10. `allowed_product_types`,
11. `allowed_currencies`,
12. `target_allocation_band`,
13. `target_concentration_limit`,
14. `mandate_restrictions`,
15. `client_preferences`.

Constraint failures must produce deterministic reason codes.

## ProposalAlternative Model

Suggested model shape:

```json
{
  "alternative_id": "alt_reduce_concentration_001",
  "label": "Reduce single-name concentration",
  "objective": "REDUCE_CONCENTRATION",
  "rank": 1,
  "status": "FEASIBLE",
  "construction_policy_version": "advisory-construction.2026-04",
  "ranking_policy_version": "advisory-ranking.2026-04",
  "intents": [],
  "simulation_result_ref": "evidence://simulation/alt_reduce_concentration_001",
  "risk_lens_ref": "evidence://risk/alt_reduce_concentration_001",
  "proposal_decision_summary": {},
  "comparison_summary": {},
  "constraint_results": [],
  "advisor_tradeoffs": [],
  "evidence_refs": []
}
```

Alternative status values:

1. `FEASIBLE`,
2. `FEASIBLE_WITH_REVIEW`,
3. `REJECTED_CONSTRAINT_VIOLATION`,
4. `REJECTED_INSUFFICIENT_EVIDENCE`,
5. `REJECTED_SIMULATION_FAILED`,
6. `REJECTED_RISK_EVIDENCE_UNAVAILABLE`,
7. `REJECTED_POLICY_BLOCKED`.

## Rejected Alternative Model

Rejected candidates are first-class evidence, not hidden implementation details.

Suggested fields:

1. `candidate_id`,
2. `objective`,
3. `status`,
4. `reason_code`,
5. `summary`,
6. `failed_constraints`,
7. `missing_evidence`,
8. `remediation`,
9. `evidence_refs`.

Rejected candidate evidence is useful because it tells the advisor why the platform cannot safely produce a requested alternative.

## Alternative Ranking Model

Ranking must be deterministic and explainable.

Initial ranking inputs:

1. feasibility status,
2. top-level proposal status,
3. RFC-0021 decision status,
4. blocking suitability issue count,
5. high-severity suitability issue count,
6. approval requirement count and severity,
7. concentration improvement,
8. risk-alignment improvement,
9. mandate-alignment posture,
10. turnover,
11. cash-floor preservation,
12. cost/friction estimate where RFC-0016 evidence exists,
13. missing-evidence count.

Tie-breakers must be stable:

1. fewer blocking issues,
2. fewer required approvals,
3. lower turnover,
4. lower missing evidence,
5. original requested objective order,
6. deterministic alternative id.

## Comparison Summary Model

Each alternative should include a UI-ready comparison summary.

Suggested fields:

1. `headline`,
2. `primary_tradeoff`,
3. `improvements`,
4. `deteriorations`,
5. `unchanged_material_factors`,
6. `approval_delta`,
7. `risk_delta`,
8. `allocation_delta`,
9. `cash_delta`,
10. `currency_delta`,
11. `cost_delta`,
12. `evidence_refs`.

The comparison summary is deterministic business evidence, not client-ready prose.

## Architecture Direction

### Construction Request Normalizer

The normalizer validates objectives and constraints and produces a canonical internal request.

Rules:

1. reject unsupported objectives with stable reason codes,
2. normalize monetary and percentage values using Decimal-safe parsing,
3. preserve request order for deterministic ranking tie-breakers,
4. separate missing evidence from invalid input.

### Candidate Generation Strategies

Each objective should map to one or more small strategy modules.

Strategy rules:

1. pure functions where possible,
2. no HTTP calls inside the strategy,
3. no hidden market-data lookup inside strategy logic,
4. no route-local strategy code,
5. candidates are provisional until canonical simulation succeeds.

### Canonical Simulation Enricher

The enricher sends every candidate to `lotus-core` and records simulation evidence.

Required behavior:

1. no local allocation or AUM calculations,
2. bounded candidate count,
3. idempotency key per candidate,
4. explicit timeout/degraded behavior,
5. traceable upstream request and response references.

### Risk Enricher

The risk enricher requests `lotus-risk` evidence for every candidate requiring risk comparison.

Missing risk evidence must produce an explicit degraded alternative status or decision-summary missing evidence item.

### Decision Summary Projector

Every feasible alternative must be evaluated through the RFC-0021 decision summary path.

The proposal-level comparison must not rank an alternative as recommended if its decision summary is blocked or insufficiently evidenced.

### Alternative Ranking Projector

The ranking projector converts enriched alternatives into deterministic ordered output.

The ranking policy must be versioned and tested independently.

## Persistence and Replay

Required behavior:

1. transient simulation may return alternatives when requested,
2. proposal create/version persists alternatives request and generated evidence,
3. async replay returns the exact persisted alternatives output after success,
4. workspace save preserves alternatives evidence,
5. workspace handoff preserves selected alternative and supporting evidence,
6. proposal artifact includes selected alternative and comparison evidence when applicable,
7. proposal replay returns persisted alternatives exactly,
8. new proposal versions regenerate alternatives only when requested or when inputs change explicitly.

## Degraded Behavior

Alternatives must degrade honestly.

Examples:

1. `lotus-core` unavailable means no feasible alternatives can be simulated,
2. `lotus-risk` unavailable means risk-ranked alternatives are insufficiently evidenced,
3. missing client profile means mandate-sensitive alternatives cannot claim suitability,
4. missing product eligibility means product-substitution alternatives cannot claim eligibility,
5. missing pricing or FX means cost or currency objectives may be rejected or downgraded.

The platform must not silently drop failed alternatives if `include_rejected_candidates` is enabled.

## API and UI Alignment

UI must consume backend-provided alternatives, rankings, comparison summaries, and rejection reasons.

UI may allow an advisor to:

1. request objectives,
2. adjust constraints,
3. select an alternative,
4. inspect comparison evidence,
5. save the selected alternative into a proposal version.

UI must not:

1. generate alternative trades locally,
2. rank alternatives locally using raw metrics,
3. hide backend rejection reasons,
4. present an alternative as suitable without backend decision evidence,
5. use AI narrative to create alternatives outside deterministic backend policy.

## Delivery Slices

### Slice 1: Current-State Assessment and Alternatives Contract Baseline

Outcome:

1. map existing proposal simulate, create, version, workspace, artifact, async, and replay paths,
2. identify where alternatives evidence must appear,
3. define additive request/response contract and OpenAPI vocabulary,
4. prove no public API v2 is required,
5. identify available upstream evidence from `lotus-core`, `lotus-risk`, and client/mandate sources.

Acceptance gate:

1. assessment document exists with code/test evidence,
2. alternatives contract is reconciled with RFC conventions,
3. unsupported initial objectives are explicitly deferred,
4. no implementation begins until contract and ownership boundaries are clear.

### Slice 2: Alternatives Models, Normalizer, and Strategy Interfaces

Outcome:

1. add alternatives request, constraint, candidate, rejected candidate, alternative, comparison, and ranking models,
2. implement request normalization and validation,
3. define construction strategy interface,
4. add first deterministic strategy skeletons without route coupling.

Acceptance gate:

1. unit tests cover valid and invalid objectives,
2. constraint validation tests cover cash, turnover, restricted instruments, preserve holdings, and missing evidence,
3. models are OpenAPI-visible where needed,
4. no upstream service calls exist inside strategy modules.

### Slice 3: Canonical Simulation and Risk Enrichment

Outcome:

1. wire candidate simulation through `lotus-core`,
2. wire candidate risk lens through `lotus-risk`,
3. preserve upstream evidence refs and degraded behavior,
4. enforce bounded candidate count and latency controls.

Acceptance gate:

1. integration tests prove each feasible candidate is simulated by `lotus-core`,
2. no local AUM/allocation calculations are introduced,
3. risk lens parity tests compare alternative evidence to direct `lotus-risk` output,
4. unavailable upstream services produce explicit rejected/degraded alternatives.

### Slice 4: Initial Construction Strategies

Outcome:

1. implement `REDUCE_CONCENTRATION`,
2. implement `RAISE_CASH`,
3. implement `LOWER_TURNOVER`,
4. implement `IMPROVE_CURRENCY_ALIGNMENT`,
5. implement `AVOID_RESTRICTED_PRODUCTS` when product eligibility evidence exists.

Acceptance gate:

1. each strategy has behavior tests with realistic portfolios,
2. infeasible constraints produce rejected candidates with reason codes,
3. generated trade intents are deterministic,
4. candidates preserve no-shorting and cash sufficiency safeguards.

### Slice 5: Decision Summary and Ranking Integration

Outcome:

1. evaluate each feasible alternative through RFC-0021 decision summary,
2. rank alternatives deterministically,
3. produce comparison summaries,
4. expose alternatives in simulation and lifecycle responses.

Acceptance gate:

1. blocked alternatives cannot rank above feasible ready alternatives,
2. missing evidence lowers confidence and ranking posture,
3. tie-breaker tests are deterministic,
4. UI-ready fields are backend-owned.

### Slice 6: Persistence, Workspace, Artifact, and Replay

Outcome:

1. persist alternatives with proposal versions,
2. preserve selected alternative in workspace save/handoff,
3. include alternatives in artifact evidence,
4. replay alternatives exactly,
5. support async replay.

Acceptance gate:

1. create/version tests prove persisted alternatives,
2. async replay tests prove exact output continuity,
3. workspace tests prove selected alternative handoff,
4. artifact tests prove comparison evidence is included,
5. new version tests prove alternatives are not stale after input changes.

### Slice 7: Live Validation and Operator Evidence

Outcome:

1. extend live validation to request alternatives on canonical seeded portfolios,
2. validate no-op, concentration, cash-raise, cross-currency, restricted-product, and degraded-upstream paths,
3. emit operator evidence for alternatives count, selected rank, rejected reasons, and latency.

Acceptance gate:

1. live suite validates at least three feasible alternatives on a canonical stack,
2. degraded `lotus-core` produces no fake alternatives,
3. degraded `lotus-risk` produces insufficient risk evidence,
4. latency impact is recorded and bounded.

### Slice 8: Documentation, Agent Context, and Branch Hygiene

Outcome:

1. update RFC status and index when implemented,
2. update API docs, workspace docs, artifact docs, and live validation docs,
3. update `REPOSITORY-ENGINEERING-CONTEXT.md` if alternatives establish durable backend-owned comparison patterns,
4. update platform or agent context if future work needs reusable guidance,
5. assess whether skill guidance should change,
6. complete PR loop, merge, delete local and remote feature branches, and sync `main`.

Acceptance gate:

1. docs distinguish implemented behavior from future roadmap,
2. context/skill changes are either made or explicitly assessed as no-change-needed,
3. RFC index is current,
4. required GitHub checks are green,
5. branch hygiene leaves `local = remote = main` after merge.

Skill/context assessment requirement:

1. Determine whether a reusable proposal-alternatives implementation playbook is needed.
2. Determine whether agent guidance should explicitly prohibit UI-generated alternatives.
3. Determine whether backend delivery guidance should add a pattern for candidate-generation plus canonical enrichment.
4. Record a no-change rationale if no context or skill update is needed.

## Test Strategy

Required test layers:

1. alternatives request normalization tests,
2. constraint validation tests,
3. candidate generation strategy tests,
4. canonical simulation integration tests,
5. risk enrichment integration tests,
6. decision summary integration tests,
7. ranking and tie-breaker tests,
8. rejected candidate tests,
9. API contract tests,
10. persistence and replay tests,
11. workspace save/handoff tests,
12. artifact tests,
13. degraded dependency tests,
14. live cross-service validation tests.

High-value scenarios:

1. reduce concentration while preserving cash floor,
2. raise cash without violating no-shorting,
3. lower turnover versus advisor's original recommendation,
4. improve currency alignment through allowed FX,
5. avoid restricted product through rejection or substitution,
6. request unsupported objective and receive stable rejection,
7. `lotus-core` unavailable and no feasible alternatives generated,
8. `lotus-risk` unavailable and risk-ranked alternatives degrade honestly,
9. selected alternative persists through workspace handoff,
10. async replay returns exact alternatives evidence.

Tests must prove business behavior. Field-presence-only tests are not sufficient.

## Performance and Scalability Expectations

Alternatives can multiply upstream calls, so the capability must be bounded.

Required behavior:

1. default `max_alternatives` must be small,
2. candidate generation must have hard limits,
3. upstream calls must be deduplicated where inputs are identical,
4. simulation and risk calls should run concurrently only within governed limits,
5. all upstream calls need timeouts and explicit degraded behavior,
6. ranking must be local and fast,
7. no unbounded universe search in the first implementation.

Latency goals:

1. normal proposal simulation without alternatives must not regress materially,
2. alternatives mode must expose timing evidence,
3. live validation must record alternatives generation latency,
4. degraded upstream calls must fail fast enough for advisor workflow usability.

## Observability and Operations

Add structured observability for:

1. alternatives requested,
2. objectives requested,
3. candidates generated,
4. candidates simulated,
5. rejected candidate counts and reason codes,
6. alternatives by status,
7. selected alternative rank,
8. upstream simulation latency,
9. upstream risk latency,
10. ranking latency,
11. degraded evidence counts.

Readiness/capabilities should expose:

1. alternatives capability enabled,
2. supported objectives,
3. supported constraints,
4. construction policy version,
5. ranking policy version,
6. upstream dependency readiness.

## Documentation Requirements

Update or add:

1. RFC implementation evidence,
2. API docs for alternatives request/response,
3. strategy and policy guide,
4. workspace guide for selected alternatives,
5. artifact guide for alternatives comparison,
6. live validation guide,
7. repository engineering context if new patterns emerge,
8. agent operating guidance if new repeatable workflows emerge.

## Naming and Vocabulary Rules

Use advisory and portfolio-construction language.

Preferred terms:

1. `proposal_alternatives`, not `variants`,
2. `construction_objectives`, not `goals` when referring to strategy inputs,
3. `constraints`, not `filters`,
4. `candidate`, not `option` before canonical simulation,
5. `alternative`, not `option` after canonical simulation,
6. `rejected_candidates`, not `errors`,
7. `comparison_summary`, not `diff_summary`,
8. `advisor_tradeoffs`, not `pros_and_cons`,
9. `ranking_policy_version`, not `sort_version`.

Reason codes must be stable upper snake case.

## Rollout and Compatibility

1. The RFC is additive and pre-live.
2. Existing proposal APIs are enhanced in place.
3. Alternatives are opt-in at first through `alternatives_request.enabled`.
4. Existing proposal behavior without alternatives must remain stable.
5. UI adoption should follow backend contract availability.
6. Alternatives may be enabled first in shadow/demo mode before becoming default advisor workflow.

## Open Questions Before Implementation

These must be resolved in Slice 1:

1. Which construction objectives should ship in the first implementation?
2. What is the first canonical product universe or eligible-instrument source?
3. Which client/mandate constraints are available from upstream services now?
4. Should alternatives be generated by default for proposal create, or only when explicitly requested?
5. Which UI surface will consume alternatives first?
6. What are acceptable latency budgets for alternatives mode?
7. Should rejected candidates be returned by default or only when requested?

## Risks and Mitigations

### Risk: Alternatives become an ungoverned optimizer

Mitigation:

1. use explicit objectives and constraints,
2. keep strategies small and deterministic,
3. require canonical simulation and decision summary before ranking,
4. reject unsupported objectives instead of guessing.

### Risk: Too many upstream calls increase latency

Mitigation:

1. bound candidate count,
2. deduplicate identical candidate requests,
3. use controlled concurrency,
4. fail fast with explicit degraded evidence.

### Risk: UI invents alternatives or rankings

Mitigation:

1. expose backend alternatives and comparison summaries,
2. document UI restrictions,
3. add contract tests for UI-required fields,
4. reject UI-only comparison logic during review.

### Risk: Alternative labels sound like advice without evidence

Mitigation:

1. labels remain short and factual,
2. decision summary determines readiness,
3. RFC-0023 narrative must consume evidence, not create recommendation facts.

## Completion Criteria

This RFC is implemented when:

1. proposal requests can ask for alternatives with explicit objectives and constraints,
2. alternatives are generated through modular deterministic strategies,
3. every feasible alternative is simulated by `lotus-core`,
4. every risk-relevant alternative is enriched by `lotus-risk` or degraded explicitly,
5. every feasible alternative has RFC-0021 decision summary evidence,
6. alternatives are ranked deterministically with stable tie-breakers,
7. rejected candidates are explainable and auditable,
8. alternatives persist and replay through lifecycle, workspace, async, and artifact paths,
9. live validation proves feasible, rejected, and degraded alternatives,
10. documentation, agent context assessment, and branch hygiene are completed in the final slice.
