# DPM Rebalance Engine Demo Scenarios

This folder contains JSON input files demonstrating key capabilities of the DPM Rebalance Engine. Run these scenarios through the API endpoints.

## Running Scenarios

### API Usage

For simulate demos, POST the content of a scenario file to `/rebalance/simulate` with `Idempotency-Key`.

Example:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-01" --data-binary "@docs/demo/01_standard_drift.json"
```

For batch what-if demos, POST to `/rebalance/analyze`:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/analyze" -H "Content-Type: application/json" --data-binary "@docs/demo/09_batch_what_if_analysis.json"
```

---

## Scenario Index

| File | Scenario | Expected Status | Key Feature |
| --- | --- | --- | --- |
| `01_standard_drift.json` | **Standard Rebalance** | `READY` | Simple Buy/Sell to align weights. |
| `02_sell_to_fund.json` | **Sell to Fund** | `READY` | Selling existing holdings to generate cash for purchases. |
| `03_multi_currency_fx.json` | **Multi-Currency** | `READY` | Auto-generation of FX Spot trades for foreign assets. |
| `04_safety_sell_only.json` | **Sell Only (Safety)** | `PENDING_REVIEW` | Prevents buying restricted assets; flags unallocated cash. |
| `05_safety_hard_block_price.json` | **DQ Block (Safety)** | `BLOCKED` | Halts execution due to missing price data. |
| `06_tax_aware_hifo.json` | **Tax-Aware HIFO** | `READY` | Tax-lot aware selling with gains budget control enabled. |
| `07_settlement_overdraft_block.json` | **Settlement Overdraft Block** | `BLOCKED` | Settlement-day cash ladder blocks run on projected overdraft. |
| `08_solver_mode.json` | **Solver Target Generation** | `READY` | Runs Stage-3 target generation in solver mode (`target_method=SOLVER`). |
| `09_batch_what_if_analysis.json` | **Batch What-If Analysis** | Mixed by scenario | Runs baseline/tax/settlement scenarios in one `/rebalance/analyze` call. |

## Feature Toggles Demonstrated

- `06_tax_aware_hifo.json`:
  - `options.enable_tax_awareness=true`
  - `options.max_realized_capital_gains=100`
- `07_settlement_overdraft_block.json`:
  - `options.enable_settlement_awareness=true`
  - `options.settlement_horizon_days=3`
- `08_solver_mode.json`:
  - `options.target_method=SOLVER`
- `09_batch_what_if_analysis.json`:
  - `scenarios.<name>.options` for per-scenario configuration in batch mode.

## Understanding Output Statuses

* **READY:** All constraints met, trades generated, safety checks passed. Ready for execution.
* **PENDING_REVIEW:** Trades generated but require human approval (e.g., cash drift, soft constraint breach).
* **BLOCKED:** Critical failure (Data Quality, Hard Constraint, Safety Violation). No trades valid.

 
