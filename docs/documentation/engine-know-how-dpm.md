# DPM Rebalance Engine Know-How

Implementation scope:
- API: `src/api/main.py` (`/rebalance/simulate`, `/rebalance/analyze`)
- Models: `src/core/models.py`
- Core orchestration: `src/core/dpm/engine.py` (`run_simulation`)
- DPM modular internals:
  - `src/core/dpm/universe.py` (universe construction and shelf filtering)
  - `src/core/dpm/targets.py` (target generation and group-constraint application)
  - `src/core/dpm/intents.py` (security intent generation, tax-aware sell controls)
  - `src/core/dpm/turnover.py` (turnover ranking and budget enforcement)
  - `src/core/dpm/execution.py` (FX generation, settlement ladder, simulation execution)
- Shared simulation primitives: `src/core/common/simulation_shared.py`
- Shared workflow gate evaluator: `src/core/common/workflow_gates.py`
- Valuation: `src/core/valuation.py`
- Rules: `src/core/compliance.py`
- Target generation: `src/core/target_generation.py`

## API Surface

### `POST /rebalance/simulate`
- Purpose: deterministic rebalance simulation.
- Required header: `Idempotency-Key`
- Optional header: `X-Correlation-Id`
- Output: `RebalanceResult` with status `READY | PENDING_REVIEW | BLOCKED` and `gate_decision`

### `POST /rebalance/analyze`
- Purpose: multi-scenario what-if analysis using shared snapshots.
- Optional header: `X-Correlation-Id`
- Output: `BatchRebalanceResult` with scenario-level results/metrics/failures.

## Pipeline (`run_simulation`)

1. Valuation
- Builds before-state via `build_simulated_state`.
- Captures data-quality buckets (`price_missing`, `fx_missing`, `shelf_missing`).

2. Universe
- Applies shelf status semantics (`APPROVED`, `RESTRICTED`, `SELL_ONLY`, `BANNED`, `SUSPENDED`).

3. Target Generation
- `HEURISTIC` or `SOLVER` path (`options.target_method`).
- Optional dual-method comparison via `compare_target_methods`.

4. Intent Generation
- Produces `SECURITY_TRADE` intents from drift.
- Applies dust suppression and optional turnover cap.
- Applies optional tax-aware lot logic (HIFO + gains budget).

5. Simulation + Rules + Reconciliation
- Generates FX funding/sweep intents.
- Optional settlement ladder checks.
- Simulates after-state and evaluates rules.
- Reconciliation guards value consistency.

## Status Semantics

- `READY`: no hard fails and no soft-rule breach.
- `PENDING_REVIEW`: at least one soft-rule fail and no hard fail.
- `BLOCKED`: any hard fail (rules, data quality, or reconciliation).

## DPM Feature Flags

- `target_method`
- `compare_target_methods`
- `enable_tax_awareness`
- `max_realized_capital_gains`
- `max_turnover_pct`
- `enable_settlement_awareness`
- `settlement_horizon_days`
- `fx_settlement_days`
- `max_overdraft_by_ccy`
- `enable_workflow_gates`
- `workflow_requires_client_consent`
- `client_consent_already_obtained`
- plus shared controls (`valuation_mode`, cash bands, dust/min-notional, data quality blocking)

## Tests That Lock DPM Behavior

- API: `tests/dpm/api/test_api_rebalance.py`
- Engine: `tests/dpm/engine/`
- Goldens: `tests/dpm/golden/test_golden_scenarios.py`
- Batch goldens: `tests/dpm/golden/test_golden_batch_analysis.py`

## Deprecation Notes

- `src/core/dpm_engine.py` is a compatibility shim and emits `DeprecationWarning`.
- Use `src/core/dpm/engine.py` as the stable DPM engine import path.
