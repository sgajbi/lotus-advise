# Rebalance Engine Know-How

This is the implementation-aligned reference for the current engine.

Scope:
- API behavior in `src/api/main.py`
- Domain models in `src/core/models.py`
- Core orchestration in `src/core/engine.py`
- Shared simulation primitives in `src/core/simulation_shared.py`
- Valuation in `src/core/valuation.py`
- Rules in `src/core/compliance.py`
- Target generation in `src/core/target_generation.py`

## 1. Current API Surface

### `POST /rebalance/simulate`

Purpose:
- Run one rebalance simulation.

Headers:
- Required: `Idempotency-Key`
- Optional: `X-Correlation-Id`

Body shape:
- `portfolio_snapshot`
- `market_data_snapshot`
- `model_portfolio`
- `shelf_entries`
- `options` (`EngineOptions`)

Response:
- `RebalanceResult`
- Domain outcomes are always `READY`, `PENDING_REVIEW`, or `BLOCKED`.
- Invalid payload/header returns `422`.

### `POST /rebalance/analyze`

Purpose:
- Run multiple named scenarios using shared snapshots.

Headers:
- Optional: `X-Correlation-Id`

Body shape:
- `portfolio_snapshot`
- `market_data_snapshot`
- `model_portfolio`
- `shelf_entries`
- `scenarios` as `Dict[str, SimulationScenario]`

Scenario key validation:
- Regex: `[a-z0-9_\-]{1,64}`
- At least one scenario required
- Maximum scenarios: `20`

Response:
- `BatchRebalanceResult` with:
  - `batch_run_id`
  - `run_at_utc` (timezone-aware ISO 8601)
  - `base_snapshot_ids`
  - `results` (successful scenarios)
  - `comparison_metrics` (successful scenarios only)
  - `failed_scenarios`
  - `warnings` (`PARTIAL_BATCH_FAILURE` when any scenario fails)

### `POST /rebalance/proposals/simulate`

Purpose:
- Run advisory proposal simulation using manual cash flows and manual trades.

Headers:
- Required: `Idempotency-Key`
- Optional: `X-Correlation-Id`

Body shape:
- `portfolio_snapshot`
- `market_data_snapshot`
- `shelf_entries`
- `options`
- `proposed_cash_flows`
- `proposed_trades`

## 2. Request/Response Model Notes

Key model details from `src/core/models.py`:
- `PortfolioSnapshot.snapshot_id` and `MarketDataSnapshot.snapshot_id` are optional.
- `Position.lots` supports optional tax-lot input for tax-aware sell allocation.
- In single-run lineage:
  - `lineage.portfolio_snapshot_id` is set from `portfolio_snapshot.portfolio_id`.
  - `lineage.market_data_snapshot_id` is currently fixed to `"md"`.
- In batch `base_snapshot_ids`:
  - portfolio id resolves as `snapshot_id` fallback `portfolio_id`.
  - market data id resolves as `snapshot_id` fallback `"md"`.
- Single-run response includes optional `tax_impact` when tax-aware mode is enabled.
- `BatchScenarioMetric` includes:
  - `status`
  - `security_intent_count`
  - `gross_turnover_notional_base` (`Money`)

## 3. Single-Run Engine Pipeline

Entrypoint:
- `run_simulation(...)` in `src/core/engine.py`

### Stage 1: Valuation

Functions:
- `build_simulated_state(...)`
- `ValuationService.value_position(...)`
- `get_fx_rate(...)`

Behavior:
- Computes position and cash values in portfolio base currency.
- Supports `valuation_mode`:
  - `CALCULATED`
  - `TRUST_SNAPSHOT` (uses `position.market_value` when provided)
- Records data quality:
  - `price_missing`
  - `fx_missing`

### Stage 2: Universe Build

Function:
- `_build_universe(...)`

Shelf semantics:
- `APPROVED`: buy and sell eligible
- `RESTRICTED`: excluded unless `allow_restricted=True`
- `SELL_ONLY`: buy blocked, weight moved to redistribution excess
- `BANNED` / `SUSPENDED`: excluded

Existing holdings not in model:
- Missing shelf -> `LOCKED_DUE_TO_MISSING_SHELF`
- Suspended/Banned/Restricted -> `LOCKED_DUE_TO_<STATUS>`
- Otherwise target set to zero for sell-down path

### Stage 3: Target Generation

Dispatcher:
- `_generate_targets(...)`
- Method selected by `options.target_method`:
  - `HEURISTIC` (default)
  - `SOLVER` (cvxpy-backed)

Heuristic path:
- `_generate_targets_heuristic(...)`
- Handles sell-only redistribution, group constraints, max position, cash buffer.

Solver path:
- `generate_targets_solver(...)` in `src/core/target_generation.py`
- Solver order is fixed: `OSQP` then `SCS`
- On infeasible/solver failures emits warnings:
  - `SOLVER_ERROR`
  - `INFEASIBLE_<STATUS>`
  - infeasibility hints (for known contradiction classes)

Optional dual-path analysis:
- `compare_target_methods=True` executes primary + alternate methods.
- Comparison output is in `explanation.target_method_comparison`.
- Divergence warnings:
  - `TARGET_METHOD_STATUS_DIVERGENCE`
  - `TARGET_METHOD_WEIGHT_DIVERGENCE`

### Stage 4: Intent Generation

Function:
- `_generate_intents(...)`

Behavior:
- Converts target drift to `SECURITY_TRADE` intents.
- Quantity uses integer floor from notional and price.
- Dust suppression:
  - threshold from `options.min_trade_notional`, else `shelf_entry.min_notional`.
  - suppressed intents are written to `diagnostics.suppressed_intents`.
- Turnover cap selection (`options.max_turnover_pct`):
  - candidate intents are ranked by drift-reduction score, then lower notional, then instrument id.
  - skip-and-continue selection is applied against turnover budget.
  - dropped candidates are written to `diagnostics.dropped_intents` with reason `TURNOVER_LIMIT`.
  - warning `PARTIAL_REBALANCE_TURNOVER_LIMIT` is added when any intent is dropped.
- Optional tax-aware sells (`options.enable_tax_awareness=True`):
  - lot-level HIFO ordering for sells when `position.lots` are present
  - run-level gains budget via `options.max_realized_capital_gains`
  - when budget binds, sell quantity is reduced and warning
    `TAX_BUDGET_LIMIT_REACHED` is emitted
  - constrained sells are captured in `diagnostics.tax_budget_constraint_events`
  - aggregate tax metrics are returned in `tax_impact`

### Stage 5: FX + Simulation + Rules + Reconciliation

Function:
- `_generate_fx_and_simulate(...)`

Behavior:
- Projects cash and creates `FX_SPOT` intents for:
  - funding negative non-base balances (`FUNDING`)
  - sweeping positive non-base balances (`SWEEP`)
- Optional settlement ladder (`options.enable_settlement_awareness=True`):
  - applies security settlement by `shelf_entry.settlement_days` (default `2`)
  - applies FX settlement by `options.fx_settlement_days` (default `2`)
  - checks projected balances from T+0 through configured horizon
    (`options.settlement_horizon_days`)
  - blocks on breaches with reason code pattern `OVERDRAFT_ON_T_PLUS_<N>`
  - writes ladder points to `diagnostics.cash_ladder` and breaches to
    `diagnostics.cash_ladder_breaches`
  - emits warning `SETTLEMENT_OVERDRAFT_UTILIZED` when configured overdraft
    is used but no breach occurs
- Adds dependencies:
  - buy intents depend on funding FX where needed
  - buy intents can depend on same-currency sells
- Applies all intents to simulated after-state.
- Evaluates rules via `RuleEngine.evaluate(...)`.
- Runs reconciliation:
  - tolerance = `0.5 + before_total * 0.0005`
  - mismatch emits hard `RECONCILIATION` fail with `VALUE_MISMATCH`

## 4. Status Semantics

Single-run status:
- `READY`: no hard fails and no pending stage condition.
- `PENDING_REVIEW`: soft-rule failure and/or stage-3 pending condition.
- `BLOCKED`: hard failure or blocking data quality.

Batch status behavior:
- No batch-level status enum.
- Each successful scenario has its own status.
- Failed scenario execution/validation is reported in `failed_scenarios`.

## 5. Rule Engine (Current Rules)

From `src/core/compliance.py`:
- `CASH_BAND` (`SOFT`)
- `SINGLE_POSITION_MAX` (`HARD`)
- `DATA_QUALITY` (`HARD`)
- `MIN_TRADE_SIZE` (`SOFT`)
- `NO_SHORTING` (`HARD`)
- `INSUFFICIENT_CASH` (`HARD`)

## 6. Key Engine Options (Current)

Implemented and active:
- `valuation_mode`
- `target_method`
- `compare_target_methods`
- `compare_target_methods_tolerance`
- `cash_band_min_weight`
- `cash_band_max_weight`
- `single_position_max_weight`
- `min_trade_notional`
- `allow_restricted`
- `suppress_dust_trades`
- `fx_buffer_pct`
- `block_on_missing_prices`
- `block_on_missing_fx`
- `min_cash_buffer_pct`
- `max_turnover_pct`
- `group_constraints`
- `enable_tax_awareness`
- `max_realized_capital_gains`
- `enable_settlement_awareness`
- `settlement_horizon_days`
- `fx_settlement_days`
- `max_overdraft_by_ccy`

Present in model but not actively consumed in core engine logic:
- `dust_trade_threshold`

## 7. Batch Analyze Semantics

Execution:
- Scenario names are processed in sorted order.
- Each scenario validates `options` independently using `EngineOptions.model_validate(...)`.

Failure isolation:
- Invalid options:
  - `failed_scenarios[name] = "INVALID_OPTIONS: ..."`
- Runtime exception:
  - `failed_scenarios[name] = "SCENARIO_EXECUTION_ERROR: <ExceptionType>"`
- Any failure adds batch warning:
  - `PARTIAL_BATCH_FAILURE`

Comparison metrics:
- Computed only for successful scenarios.
- `gross_turnover_notional_base` is the sum of `notional_base.amount` for `SECURITY_TRADE` intents.
- Batch metrics currently do not include tax-impact comparisons.
- A no-trade scenario yields:
  - `security_intent_count = 0`
  - `gross_turnover_notional_base.amount = 0`

## 8. Implementation Status Matrix

Implemented RFC slices:
- RFC-0001 to RFC-0008
- RFC-0009 (tax-aware HIFO sells and gains budget; request-scoped toggle via `enable_tax_awareness`)
- RFC-0010 (turnover cap control)
- RFC-0011 (settlement awareness; request-scoped toggle via `enable_settlement_awareness`)
- RFC-0012 (solver integration; selectable by `target_method`)
- RFC-0013 (batch what-if analysis)

Explicitly deferred:
- Deferred backlog is consolidated under RFC-0015:
  - persistence-backed idempotency/run storage
  - explicit transaction cost model and partial sizing
  - batch-level tax-impact comparison metrics
  - advanced tax/settlement policy variants

## 9. Practical Examples

### Example A: Single-run simulate

```bash
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-1" \
  -d @docs/sample_request.json
```

See:
- `docs/sample_request.json`
- `docs/sample_response.json`

### Example B: Batch analyze with one valid and one invalid scenario

```json
{
  "portfolio_snapshot": { "...": "shared" },
  "market_data_snapshot": { "...": "shared" },
  "model_portfolio": { "...": "shared" },
  "shelf_entries": [{ "...": "shared" }],
  "scenarios": {
    "baseline": { "options": {} },
    "invalid_case": {
      "options": {
        "group_constraints": {
          "sectorTECH": { "max_weight": "0.2" }
        }
      }
    }
  }
}
```

Expected:
- `baseline` in `results` and `comparison_metrics`
- `invalid_case` in `failed_scenarios`
- `warnings` includes `PARTIAL_BATCH_FAILURE`

Reference tests:
- `tests/api/test_api_rebalance.py`
- `tests/golden/test_golden_batch_analysis.py`

### Example C: Zero-turnover batch metric

Reference scenario:
- `tests/golden_data/scenario_13_zero_turnover_batch.json`

Expected metric:
- `security_intent_count = 0`
- `gross_turnover_notional_base.amount = "0"`

## 10. Where Behavior Is Locked by Tests

Primary suites:
- API contracts: `tests/api/test_api_rebalance.py`
- Model contracts: `tests/contracts/test_contract_models.py`
- Golden single-run: `tests/golden/test_golden_scenarios.py`
- Golden batch: `tests/golden/test_golden_batch_analysis.py`
- Engine behavior: `tests/engine/`

When changing behavior:
- Update code, tests, and this document in the same slice.
- If behavior change is intentional, update or add golden files under `tests/golden_data/`.

## 11. Feature Catalog (What Exists and How to Enable)

This section is a quick reference for all currently supported engine features.

### 11.1 Always-On Core Features

1. Canonical simulation endpoint
- What it does: runs full rebalance simulation and returns audit bundle.
- Where: `POST /rebalance/simulate`.
- How to enable: always on.

2. Deterministic pipeline execution
- What it does: fixed stage order (valuation, universe, targets, intents, simulation/rules/reconciliation).
- How to enable: always on.

3. Shelf status enforcement
- What it does: enforces `APPROVED`, `RESTRICTED`, `SELL_ONLY`, `SUSPENDED`, `BANNED`.
- How to enable: always on; `allow_restricted` can relax restricted exclusion.

4. Post-trade safety checks
- What it does: checks no-shorting, insufficient cash, and reconciliation mismatch hard blocks.
- How to enable: always on.

5. No-throw domain outcomes
- What it does: valid payloads return `READY`, `PENDING_REVIEW`, or `BLOCKED` with diagnostics.
- How to enable: always on.

### 11.2 Configurable Features (Request Options)

1. Valuation policy
- What it does: controls whether valuation uses computed price/FX or trusted snapshot market values.
- Option: `options.valuation_mode`.
- Values: `CALCULATED` (default), `TRUST_SNAPSHOT`.

2. Target generation method
- What it does: chooses heuristic target generation or solver optimization.
- Option: `options.target_method`.
- Values: `HEURISTIC` (default), `SOLVER`.

3. Target method comparison
- What it does: runs primary and alternate target methods and reports divergence.
- Option: `options.compare_target_methods=true`.
- Tolerance option: `options.compare_target_methods_tolerance`.

4. Cash band policy
- What it does: evaluates soft cash allocation bounds in compliance checks.
- Options: `options.cash_band_min_weight`, `options.cash_band_max_weight`.

5. Single-position cap
- What it does: caps concentration and can force `PENDING_REVIEW`.
- Option: `options.single_position_max_weight`.

6. Minimum trade notional and dust suppression
- What it does: suppresses micro-trades under configured threshold.
- Options:
  - `options.suppress_dust_trades` (default `true`)
  - `options.min_trade_notional` (request-level threshold)
  - fallback from `shelf_entry.min_notional`.

7. Missing-data blocking policy
- What it does: controls whether missing prices/FX are hard-blocking.
- Options:
  - `options.block_on_missing_prices` (default `true`)
  - `options.block_on_missing_fx` (default `true`).

8. FX funding buffer
- What it does: applies buffer to FX funding amount for negative currency balances.
- Option: `options.fx_buffer_pct`.

9. Minimum cash buffer in target generation
- What it does: scales tradeable target weights to preserve required cash.
- Option: `options.min_cash_buffer_pct`.

10. Group constraints (RFC-0008)
- What it does: caps attribute groups (for example sector) and redistributes excess.
- Option: `options.group_constraints`.
- Key format: `<attribute_key>:<attribute_value>`, for example `sector:TECH`.

11. Turnover cap (RFC-0010)
- What it does: applies deterministic skip-and-continue selection under turnover budget.
- Option: `options.max_turnover_pct`.
- Diagnostics:
  - dropped intents with `reason=TURNOVER_LIMIT`
  - warning `PARTIAL_REBALANCE_TURNOVER_LIMIT`.

12. Tax-aware sell allocation (RFC-0009)
- What it does: uses HIFO lot ordering when lots are available and enforces optional gains budget.
- Required position data: `position.lots` for lot-aware behavior.
- Options:
  - `options.enable_tax_awareness=true`
  - `options.max_realized_capital_gains` (optional cap).
- Outputs:
  - `tax_impact`
  - `diagnostics.tax_budget_constraint_events`
  - warning `TAX_BUDGET_LIMIT_REACHED` when budget binds.

13. Settlement-aware cash ladder (RFC-0011)
- What it does: checks projected cash by settlement day and blocks on overdraft breaches.
- Options:
  - `options.enable_settlement_awareness=true`
  - `options.settlement_horizon_days`
  - `options.fx_settlement_days`
  - `options.max_overdraft_by_ccy`.
- Instrument input: `shelf_entry.settlement_days` (default `2`).
- Outputs:
  - `diagnostics.cash_ladder`
  - `diagnostics.cash_ladder_breaches`
  - warning `SETTLEMENT_OVERDRAFT_UTILIZED` when overdraft is used but within limit.

14. Advisory proposal simulation controls (RFC-0014A)
- What it does: enables proposal endpoint behavior and cash-flow ordering/guards.
- Options:
  - `options.enable_proposal_simulation`
  - `options.proposal_apply_cash_flows_first`
  - `options.proposal_block_negative_cash`

### 11.3 Batch Analysis Features

1. Multi-scenario batch simulation (RFC-0013)
- What it does: runs many named scenarios over shared snapshots in one request.
- Where: `POST /rebalance/analyze`.
- How to enable: provide `scenarios` map in request body.

2. Per-scenario options
- What it does: each scenario can override `EngineOptions` independently.
- How to enable: set `scenarios.<name>.options`.

3. Batch comparison metrics
- What it does: returns per-scenario status, security intent count, and turnover proxy.
- How to enable: always on for successful scenarios.
