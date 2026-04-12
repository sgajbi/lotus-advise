# RFC-0022 Slice 4 Evidence: Initial Construction Strategies

- RFC: `docs/rfcs/RFC-0022-proposal-alternatives-and-portfolio-construction-workbench.md`
- Slice: 4
- Date: 2026-04-13
- Status: Completed

## Scope

This slice replaces the earlier strategy placeholders with deterministic, bounded construction
behavior for the first four objective families:

1. `REDUCE_CONCENTRATION`
2. `RAISE_CASH`
3. `LOWER_TURNOVER`
4. `IMPROVE_CURRENCY_ALIGNMENT`

It also upgrades the strategy layer so it can return explicit pre-simulation rejected candidates
when the requested objective cannot be produced truthfully from local baseline inputs.

## Delivered

### 1. Richer local strategy inputs

`src/core/advisory/alternatives_strategies.py` now models strategy-local data explicitly:

1. `StrategyPosition`
2. `StrategyShelfInstrument`
3. `StrategyTradeIntent`
4. `AlternativeStrategyInputs.cash_balances`

That keeps strategy generation deterministic and self-contained without introducing upstream calls.

### 2. Strategy-time rejection support

Added `AlternativeStrategyBuildResult` and `build_candidate_plan`.

This was necessary because Slice 4 acceptance requires infeasible constraints to produce rejected
candidates with stable reason codes instead of silently returning no candidate.

`build_candidate_seeds` remains available as a compatibility wrapper over the richer build plan.

### 3. Real deterministic strategy behavior

Implemented:

1. concentration reduction by selling half of the largest sellable holding and rotating into an
   approved base-currency replacement,
2. cash raising by selling a base-currency holding sized to the explicit cash-floor shortfall,
3. turnover reduction by halving an adjustable baseline trade,
4. currency alignment by rotating part of a non-aligned holding into an approved base-currency
   replacement.

All outputs remain bounded, deterministic, and no-shorting by construction.

### 4. Explicit deferred handling for restricted-product alternatives

`AVOID_RESTRICTED_PRODUCTS` still does not pseudo-ship.

The strategy now returns an explicit `REJECTED_INSUFFICIENT_EVIDENCE` outcome with
`ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE` until canonical eligibility evidence is ready.

## Tests Added Or Tightened

Updated `tests/unit/advisory/engine/test_engine_proposal_alternatives.py`.

The slice now proves:

1. strategy generation is deterministic,
2. concentration strategy emits concrete sell and buy intents,
3. cash-raising strategy sizes a sell against a real cash-floor shortfall,
4. turnover strategy reduces a baseline trade rather than inventing a new one,
5. currency-alignment strategy rotates a misaligned holding into base-currency exposure,
6. infeasible constraints return rejected candidates with stable reason codes,
7. restricted-product alternatives remain explicitly deferred rather than falsely supported.

## Review Notes

The important tightening decision in this slice was architectural, not cosmetic:

1. strategy generation must be able to return both seeds and rejected candidates,
2. otherwise Slice 4 cannot satisfy its own RFC acceptance gate truthfully,
3. the old seed-only interface would have forced silent drops for infeasible objectives.

That gap is now closed while preserving a backward-compatible seed-only helper.

## Remaining For Later Slices

Still intentionally deferred:

1. ranking and comparison summaries,
2. public API exposure,
3. persistence and replay wiring,
4. live-stack alternatives validation.
