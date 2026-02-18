# Rebalance Engine Know-How

This is the implementation-aligned reference for the current engine.

Scope:
- API behavior in `src/api/main.py`
- Domain models in `src/core/models.py`
- Core orchestration in `src/core/engine.py`
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

## 2. Request/Response Model Notes

Key model details from `src/core/models.py`:
- `PortfolioSnapshot.snapshot_id` and `MarketDataSnapshot.snapshot_id` are optional.
- In single-run lineage:
  - `lineage.portfolio_snapshot_id` is set from `portfolio_snapshot.portfolio_id`.
  - `lineage.market_data_snapshot_id` is currently fixed to `"md"`.
- In batch `base_snapshot_ids`:
  - portfolio id resolves as `snapshot_id` fallback `portfolio_id`.
  - market data id resolves as `snapshot_id` fallback `"md"`.
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

### Stage 5: FX + Simulation + Rules + Reconciliation

Function:
- `_generate_fx_and_simulate(...)`

Behavior:
- Projects cash and creates `FX_SPOT` intents for:
  - funding negative non-base balances (`FUNDING`)
  - sweeping positive non-base balances (`SWEEP`)
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
- `group_constraints`

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
- A no-trade scenario yields:
  - `security_intent_count = 0`
  - `gross_turnover_notional_base.amount = 0`

## 8. Implementation Status Matrix

Implemented RFC slices:
- RFC-0001 to RFC-0008
- RFC-0012 (solver integration; selectable by `target_method`)
- RFC-0013 (batch what-if analysis)

Explicitly deferred:
- RFC-0009 tax-aware controls and tax-impact metrics
- RFC-0010 turnover/cost controls as explicit optimization terms
- RFC-0011 settlement ladder and overdraft policy mechanics

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
