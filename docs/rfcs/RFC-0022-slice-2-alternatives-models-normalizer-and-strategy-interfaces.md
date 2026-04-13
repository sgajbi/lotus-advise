# RFC-0022 Slice 2: Alternatives Models, Normalizer, and Strategy Interfaces

- RFC: `RFC-0022`
- Slice: `Slice 2`
- Status: COMPLETED
- Created: 2026-04-13
- Owners: lotus-advise

## Purpose

This document is the Slice 2 evidence artifact for RFC-0022.

Its role is to prove that `lotus-advise` now has a modular internal alternatives foundation before any cross-service simulation, ranking projection, or persistence wiring begins.

## Implemented Scope

Slice 2 is implemented in these files:

1. `src/core/advisory/alternatives_models.py`
2. `src/core/advisory/alternatives_normalizer.py`
3. `src/core/advisory/alternatives_strategies.py`
4. `src/core/advisory/__init__.py`
5. `tests/unit/advisory/contracts/test_contract_proposal_alternatives_models.py`
6. `tests/unit/advisory/engine/test_engine_proposal_alternatives.py`

## What Was Added

### Dedicated Advisory Alternatives Models

The slice introduces dedicated alternatives models under `src/core/advisory/` instead of expanding the existing shared proposal monolith in `src/core/models.py`.

Implemented model groups:

1. request and constraints models,
2. candidate seed model,
3. rejected candidate model,
4. ranked alternative model,
5. comparison summary model,
6. ranking projection model,
7. constraint-result and tradeoff models.

Assessment:

1. this keeps alternatives modular and advisory-owned,
2. it avoids polluting shared simulation contracts before the feature is wired end-to-end,
3. it reduces future merge pressure on `src/core/models.py`.

### Request Normalization And Validation

The slice adds a dedicated normalizer that:

1. enforces first-implementation max-alternatives bounds,
2. rejects explicitly deferred objectives,
3. rejects `selected_alternative_id` on first-time generation requests,
4. retains selection-mode support for later lifecycle/workspace writes,
5. classifies missing evidence requirements for conditional scope such as restricted-product avoidance and mandate/client context.

Assessment:

1. first-scope rules now live in one reusable normalization seam,
2. missing-evidence handling is explicit rather than hidden in future strategy code,
3. later slices can reuse the normalized request contract consistently across simulate, lifecycle, and workspace paths.

### Deterministic Strategy Interfaces

The slice adds a route-independent strategy interface and first strategy registry for:

1. `REDUCE_CONCENTRATION`
2. `RAISE_CASH`
3. `LOWER_TURNOVER`
4. `IMPROVE_CURRENCY_ALIGNMENT`
5. `AVOID_RESTRICTED_PRODUCTS`

Current strategy behavior:

1. build deterministic candidate seeds only,
2. do not call upstream services,
3. do not generate fake simulated alternatives,
4. preserve objective order and deterministic candidate ids.

Assessment:

1. this gives later slices a stable insertion point for actual construction logic,
2. the current slice remains truthful because it does not pretend the strategies are complete,
3. strategy modules remain decoupled from API routes and integration clients.

## High-Value Tests Added

Contract coverage:

1. request defaults and bounded contract behavior,
2. constraint normalization and deduplication,
3. float and turnover-range rejection,
4. alternative model acceptance of canonical decision-summary payload shape.

Engine coverage:

1. deferred objective rejection,
2. selected-alternative misuse rejection on generation,
3. missing-evidence classification for conditional objective scope,
4. max-alternatives bound enforcement,
5. deterministic candidate-seed generation and objective ordering,
6. strategy operation without upstream-call context.

## Review Pass

Post-implementation review conclusions:

1. alternatives contracts are now in a dedicated advisory module rather than being mixed into unrelated workflow or simulation code,
2. no dead code or hidden half-wired route behavior was introduced,
3. no public API route was widened before backend behavior exists,
4. current slice remains implementation-truthful and does not overclaim feature readiness.

## Validation

Repository-native validation run:

1. `make check`

Result:

1. passed

## Exit Decision

Slice 2 is complete.

The repository now has:

1. a modular alternatives contract foundation,
2. a reusable normalizer for first-scope policy,
3. deterministic strategy skeletons with no route coupling,
4. meaningful unit coverage for the new behavior.

The next slice can now focus on canonical simulation and risk enrichment wiring without reopening basic alternatives contract design.
