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
5. first implementation risk comparison is limited to the currently implemented RFC-0020 proposal risk lens unless a later RFC expands authoritative risk scope,
6. no UI surface invents an alternative that cannot be reproduced by backend evidence,
7. every alternative is auditable, replayable, and explainable.

Because `lotus-advise` is not live and callers are controlled, this RFC enhances existing APIs in place. It does not introduce public `/v2` APIs or duplicate simulation contracts.

The first implementation is intentionally narrower than the full target-state vocabulary. It
should ship a governed advisory-alternatives baseline, not an over-ambitious optimizer:

1. explicit advisor-requested alternatives only,
2. a bounded candidate count,
3. a governed candidate universe sourced from held positions plus canonical shelf evidence,
4. deterministic ranking and rejection reasons,
5. persisted and replay-safe alternatives evidence,
6. no AI-generated trades and no unrestricted market search.

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

This RFC makes alternatives a backend-governed advisory capability while preserving clear domain
authority boundaries.

It also narrows implementation posture up front:

1. `lotus-advise` may orchestrate heuristics and strategy composition,
2. `lotus-advise` must not become a hidden optimizer or discretionary portfolio-construction
   engine,
3. unsupported objectives must be rejected explicitly instead of partially guessed.

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
7. auditable linkage between each alternative and its construction objective,
8. immutable selected-alternative semantics through proposal versioning and workspace handoff.

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

The first implementation must therefore optimize for truthful bounded comparison, not breadth:

1. small deterministic strategy modules,
2. explicit rejection over silent fallback,
3. canonical simulation and risk enrichment before ranking,
4. persisted selection semantics that survive replay and lifecycle reads.

## Requirement Traceability

| Requirement | RFC Section | Acceptance Evidence Required |
| --- | --- | --- |
| Alternatives must be backend-owned | Target API Contract, API and UI Alignment | API, artifact, and workspace tests prove alternatives are returned from backend evidence |
| Canonical calculations must remain in upstream services | Domain Authority Boundaries | Tests prove alternatives call `lotus-core` for simulation and do not recalculate AUM/allocation locally |
| Risk lens must remain authoritative in `lotus-risk` | Domain Authority Boundaries | Integration tests compare alternative risk evidence to direct risk-service output |
| Alternatives must include rejected candidates | Rejected Alternative Model | Tests prove infeasible candidates return reason codes rather than disappearing silently |
| Ranking must be deterministic | Alternative Ranking Model | Pure ranking tests cover tie-breakers and policy precedence |
| UI must not invent comparison logic | API and UI Alignment | Contract exposes comparison and ranking fields needed by UI |
| Selected alternative state must be immutable per persisted version | ProposalAlternative Model, Persistence and Replay | Persistence and replay tests prove exactly one selected alternative survives version reads and workspace handoff |
| Persisted alternatives must replay without silent recomputation | Optional Projection Endpoint, Persistence and Replay | Replay tests prove persisted alternatives and ranks remain unchanged under fresher upstream state |
| Candidate generation must remain bounded and governed | Pre-Live Contract Hardening Decision, Performance and Scalability Expectations | Unit and integration tests prove hard candidate caps, deduplicated upstream calls, and no unrestricted search |
| Final slice must assess durable guidance and branch hygiene | Slice 8 | Final evidence records context/skill decision, PR merge proof, and `local = remote = main` hygiene |
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

## Non-Negotiable Invariants

These invariants must remain true in every implementation slice:

1. a candidate becomes an `alternative` only after canonical `lotus-core` simulation succeeds,
2. a feasible ranked alternative must carry canonical simulation lineage, applicable risk evidence,
   and RFC-0021 decision posture,
3. `lotus-advise` must not compute local AUM, allocation, valuation, cash, or risk metrics to fill
   alternatives gaps,
4. rejected candidates remain persisted evidence when `include_rejected_candidates = true`; they
   must not disappear silently between simulate, create, version, workspace, artifact, and replay
   views,
5. at most one alternative may be selected per persisted proposal version,
6. persisted alternatives, ranks, and selected state must replay exactly and must not be silently
   recomputed against fresher upstream data,
7. UI may select only from backend-generated alternatives and must not mutate generated intents
   locally,
8. candidate generation, enrichment concurrency, and upstream calls must remain explicitly bounded
   and policy-governed,
9. every ranked outcome must remain explainable through stable policy versions and reason codes,
10. alternative comparison must reuse RFC-0020 proposal allocation dimensions and the canonical
    RFC-0021 `proposal_decision_summary` contract rather than introducing parallel advisory-local
    summaries.

## Pre-Live Contract Hardening Decision

Because the app is not live, this RFC enhances existing contracts in place.

Allowed changes:

1. additive fields on proposal simulation, create, version, workspace, artifact, and replay responses,
2. new internal model names for construction objectives, constraints, alternatives, rankings, and rejection reasons,
3. optional read-only endpoints under existing `/advisory/proposals/...` route family,
4. internal construction-policy versions and ranking-policy versions.

Required first-implementation decisions:

1. alternatives remain opt-in through `alternatives_request.enabled`,
2. the first implementation must not generate alternatives implicitly on every proposal,
3. the first implementation must use a bounded internal candidate universe rather than unrestricted
   security search,
4. the first implementation must prefer additive fields on existing proposal and workspace
   responses over new write routes.

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

`lotus-advise` may reuse:

1. the RFC-0020 canonical proposal allocation lens and curated proposal dimensions,
2. the RFC-0020 canonical proposal concentration risk lens,
3. the RFC-0021 `proposal_decision_summary` contract for each generated feasible alternative.

`lotus-advise` does not own:

1. unconstrained optimizer search,
2. client-ready narrative for alternatives,
3. local valuation, allocation, or risk calculation,
4. security-master expansion beyond governed upstream evidence.

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
    "ranking_policy_id": "advisory-alternative-ranking.2026-04",
    "include_rejected_candidates": true
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

1. `GET /advisory/proposals/{proposal_id}/versions/{version_no}/alternatives`

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
8. `evidence_requirements`,
9. `selected_alternative_id`.

Rules:

1. `max_alternatives` is an output bound, not permission for unbounded candidate generation,
2. `selected_alternative_id` is valid only when it references a generated feasible alternative from
   the same request or persisted version,
3. `selected_alternative_id` should be absent on first-time generation requests and used only on
   lifecycle or workspace writes that confirm a previously generated alternative selection,
4. `include_rejected_candidates` should default to `true` for advisor and operator surfaces in the
   first implementation so unsupported or infeasible objectives remain visible.

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

Initial implementation scope:

1. ship first with `REDUCE_CONCENTRATION`, `RAISE_CASH`, `LOWER_TURNOVER`, and
   `IMPROVE_CURRENCY_ALIGNMENT`,
2. allow `AVOID_RESTRICTED_PRODUCTS` only when canonical product-eligibility or restricted-product
   evidence is already available,
3. defer `REBALANCE_TO_REFERENCE_MODEL`, `MINIMIZE_APPROVAL_REQUIREMENTS`,
   `PRESERVE_CLIENT_PREFERENCES`, and `LOWER_COST_AND_FRICTION` unless Slice 1 proves the required
   upstream evidence and ranking policy are ready,
4. reject deferred objectives explicitly with stable reason codes rather than silently ignoring
   them.

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

Initial implementation scope:

1. ship first with `cash_floor`, `max_turnover_pct`, `max_trade_count`, `preserve_holdings`,
   `restricted_instruments`, `do_not_buy`, `do_not_sell`, `allow_fx`, and `allowed_currencies`,
2. treat `mandate_restrictions` and `client_preferences` as pass-through evidence inputs only when
   canonical upstream context is available,
3. defer broad `target_allocation_band` and `target_concentration_limit` tuning until the first
   construction strategies are stable.

## ProposalAlternative Model

Suggested model shape:

```json
{
  "alternative_id": "alt_reduce_concentration_001",
  "label": "Reduce single-name concentration",
  "objective": "REDUCE_CONCENTRATION",
  "rank": 1,
  "selected": false,
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

Rules:

1. `rank` is assigned only among feasible or feasible-with-review alternatives,
2. `selected = true` is allowed for at most one persisted alternative per proposal version,
3. a rejected alternative must never carry a selected flag,
4. `proposal_decision_summary` must use the canonical RFC-0021 shape and vocabulary rather than an
   alternatives-specific summary schema.

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
8. risk-alignment improvement within the currently implemented canonical proposal risk-lens scope,
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

Ranking policy rules:

1. rejected alternatives are never interleaved into feasible ranks,
2. `FEASIBLE` alternatives rank above `FEASIBLE_WITH_REVIEW` unless an explicit policy version says
   otherwise,
3. an alternative with `INSUFFICIENT_EVIDENCE` or blocked RFC-0021 decision posture must never rank
   above a fully evidenced feasible alternative,
4. the ranking projector must emit ranking reasons so operator evidence can explain why rank `1`
   won.

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

Comparison scope rules:

1. allocation deltas must be derived from the RFC-0020 canonical proposal allocation lens and its
   curated proposal dimensions,
2. first implementation risk comparison must remain limited to the currently implemented canonical
   proposal concentration risk lens unless a later RFC expands authoritative risk coverage,
3. comparison summaries must not imply broader optimization across unavailable risk methodologies.

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

Strategy governance:

1. each strategy must emit provenance metadata describing which objective and rule path created the
   candidate,
2. strategy output must be deterministic for identical normalized input and evidence order,
3. strategies must prefer modifying governed held or already-shelved instruments in the first
   implementation,
4. if a strategy requires unavailable product-substitution evidence, it must emit a rejected
   candidate rather than searching heuristically.

### Canonical Simulation Enricher

The enricher sends every candidate to `lotus-core` and records simulation evidence.

Required behavior:

1. no local allocation or AUM calculations,
2. bounded candidate count,
3. idempotency key per candidate,
4. explicit timeout/degraded behavior,
5. traceable upstream request and response references,
6. deduplicate simulation calls when normalized candidate inputs are identical,
7. preserve candidate-to-upstream lineage for replay and operator evidence.

### Risk Enricher

The risk enricher requests `lotus-risk` evidence for every candidate requiring risk comparison.

Missing risk evidence must produce an explicit degraded alternative status or decision-summary missing evidence item.

### Decision Summary Projector

Every feasible alternative must be evaluated through the RFC-0021 decision summary path.

The proposal-level comparison must not rank an alternative as recommended if its decision summary is blocked or insufficiently evidenced.

### Alternative Ranking Projector

The ranking projector converts enriched alternatives into deterministic ordered output.

The ranking policy must be versioned and tested independently.

The ranking projector must also expose:

1. `ranking_reason_codes`,
2. `ranked_against_alternative_ids`,
3. stable comparator inputs used for final ordering.

## Persistence and Replay

Required behavior:

1. transient simulation may return alternatives when requested,
2. proposal create/version persists alternatives request and generated evidence,
3. async replay returns the exact persisted alternatives output after success,
4. workspace save preserves alternatives evidence,
5. workspace handoff preserves selected alternative and supporting evidence,
6. proposal artifact includes selected alternative and comparison evidence when applicable,
7. proposal replay returns persisted alternatives exactly,
8. new proposal versions regenerate alternatives only when requested or when inputs change explicitly,
9. persisted proposal versions must not silently recompute rankings or selected alternatives
   against fresher upstream state.

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

UI selection rule:

1. UI may select among backend-generated alternatives,
2. UI must persist only a backend-issued alternative id back through supported backend fields,
3. UI must not mutate generated trade intents locally after an alternative is selected.

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
4. no implementation begins until contract and ownership boundaries are clear,
5. first-implementation objective and constraint scope is frozen explicitly.

Evidence document for this slice should be recorded in:

1. `docs/rfcs/RFC-0022-slice-1-current-state-assessment-and-contract-baseline.md`

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

Evidence document for this slice should be recorded in:

1. `docs/rfcs/RFC-0022-slice-2-alternatives-models-normalizer-and-strategy-interfaces.md`

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

Evidence document for this slice should be recorded in:

1. `docs/rfcs/RFC-0022-slice-3-canonical-simulation-and-risk-enrichment.md`

### Slice 4: Initial Construction Strategies

Outcome:

1. implement `REDUCE_CONCENTRATION`,
2. implement `RAISE_CASH`,
3. implement `LOWER_TURNOVER`,
4. implement `IMPROVE_CURRENCY_ALIGNMENT`.

Conditional scope:

1. `AVOID_RESTRICTED_PRODUCTS` ships in this slice only if Slice 1 proves canonical product
   eligibility or restriction evidence is available and testable,
2. otherwise it remains explicitly deferred with no placeholder pseudo-support.

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
4. UI-ready fields are backend-owned,
5. selected alternative semantics are deterministic and replay-safe.

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
5. new version tests prove alternatives are not stale after input changes,
6. persisted version reads prove selected alternative and ranking order are not silently recomputed.

### Slice 7: Live Validation and Operator Evidence

Outcome:

1. extend live validation to request alternatives on canonical seeded portfolios,
2. validate no-op, concentration, cash-raise, cross-currency, restricted-product, and degraded-upstream paths,
3. emit operator evidence for alternatives count, selected rank, rejected reasons, and latency.

Acceptance gate:

1. live suite validates at least three feasible alternatives on a canonical stack,
2. degraded `lotus-core` produces no fake alternatives,
3. degraded `lotus-risk` produces insufficient risk evidence,
4. latency impact is recorded and bounded,
5. operator evidence records why top-ranked alternatives outranked the others.

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
2. default `max_alternatives` should be `3` in the first implementation unless Slice 1 evidence
   proves a different bound is safe,
3. candidate generation must have hard limits,
4. upstream calls must be deduplicated where inputs are identical,
5. simulation and risk calls should run concurrently only within governed limits,
6. all upstream calls need timeouts and explicit degraded behavior,
7. ranking must be local and fast,
8. no unbounded universe search in the first implementation.

Concurrency guardrails:

1. candidate enrichment concurrency should be explicitly bounded by configuration,
2. first implementation should prefer a small fixed worker limit over adaptive concurrency,
3. timeout or upstream-rate failures must surface as deterministic rejected or degraded outcomes,
   not partial silent omission.

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
6. upstream dependency readiness,
7. current default `max_alternatives`,
8. whether rejected candidates are included by default.

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

## Resolved Design Decisions Before Implementation

These decisions are intentionally fixed before Slice 1 implementation begins:

1. no public `/v2` APIs are required,
2. alternatives are opt-in in the first implementation,
3. first implementation objective scope is intentionally narrow,
4. first implementation uses a governed candidate universe rather than unrestricted security
   search,
5. `GET /advisory/proposals/{proposal_id}/versions/{version_no}/alternatives` is the only
   acceptable optional read projection if a dedicated endpoint is needed,
6. selected alternative state must be persisted and replay-safe.

## Open Questions Before Implementation

These must be resolved in Slice 1:

1. What exact canonical product universe or eligible-instrument source is available for the first
   release?
2. Which client/mandate constraints are available from upstream services now with sufficient
   reliability?
3. Which UI surface will consume alternatives first?
4. What exact latency budgets are acceptable for alternatives mode on canonical seeded portfolios?
5. Can `AVOID_RESTRICTED_PRODUCTS` ship in Slice 4 with truthful upstream evidence, or should it
   remain deferred after Slice 1 discovery?

## Risks and Mitigations

### Risk: Alternatives become an ungoverned optimizer

Mitigation:

1. use explicit objectives and constraints,
2. keep strategies small and deterministic,
3. require canonical simulation and decision summary before ranking,
4. reject unsupported objectives instead of guessing,
5. freeze the first implementation to a governed initial strategy set instead of expanding scope
   opportunistically during delivery.

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
