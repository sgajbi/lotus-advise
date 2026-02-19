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

For advisory proposal simulation demos, POST to `/rebalance/proposals/simulate`:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/proposals/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-proposal-01" --data-binary "@docs/demo/10_advisory_proposal_simulate.json"
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
| `10_advisory_proposal_simulate.json` | **Advisory Proposal Simulation** | `READY` | Simulates manual cash flows and manual trades in `/rebalance/proposals/simulate`. |
| `11_advisory_auto_funding_single_ccy.json` | **Advisory Auto-Funding (Single CCY)** | `READY` | Generates funding `FX_SPOT` and links BUY dependency. |
| `12_advisory_partial_funding.json` | **Advisory Partial Funding** | `READY` | Uses existing foreign cash first, then tops up with FX. |
| `13_advisory_missing_fx_blocked.json` | **Advisory Missing FX (Blocked)** | `BLOCKED` | Blocks advisory proposal when required FX funding pair is missing. |
| `14_advisory_drift_asset_class.json` | **Advisory Drift Analytics (Asset Class)** | `READY` | Returns `drift_analysis.asset_class` against inline `reference_model`. |
| `15_advisory_drift_instrument.json` | **Advisory Drift Analytics (Instrument)** | `READY` | Returns both asset-class and instrument drift with unmodeled exposures. |
| `16_advisory_suitability_resolved_single_position.json` | **Suitability Resolved Concentration** | `READY` | Returns a `RESOLVED` single-position issue after proposal trades. |
| `17_advisory_suitability_new_issuer_breach.json` | **Suitability New Issuer Breach** | `READY` | Returns a `NEW` high-severity issuer concentration issue and gate recommendation. |
| `18_advisory_suitability_sell_only_violation.json` | **Suitability Sell-Only Violation** | `BLOCKED` | Returns a `NEW` governance issue when proposal attempts BUY in `SELL_ONLY`. |

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
- `10_advisory_proposal_simulate.json`:
  - `options.enable_proposal_simulation=true`
  - `options.proposal_apply_cash_flows_first=true`
  - `options.proposal_block_negative_cash=true`
- `11_advisory_auto_funding_single_ccy.json`:
  - `options.auto_funding=true`
  - `options.funding_mode=AUTO_FX`
  - `options.fx_generation_policy=ONE_FX_PER_CCY`
- `12_advisory_partial_funding.json`:
  - `options.auto_funding=true`
  - existing foreign cash + FX top-up behavior
- `13_advisory_missing_fx_blocked.json`:
  - `options.block_on_missing_fx=true`
  - hard block + missing FX diagnostics
- `14_advisory_drift_asset_class.json`:
  - `options.enable_drift_analytics=true`
  - `reference_model.asset_class_targets` controls drift comparison buckets
- `15_advisory_drift_instrument.json`:
  - `options.enable_instrument_drift=true`
  - `reference_model.instrument_targets` enables instrument-level drift output
- `16_advisory_suitability_resolved_single_position.json`:
  - `options.enable_suitability_scanner=true`
  - `options.suitability_thresholds.single_position_max_weight=0.10`
- `17_advisory_suitability_new_issuer_breach.json`:
  - `options.enable_suitability_scanner=true`
  - `options.suitability_thresholds.issuer_max_weight=0.20`
- `18_advisory_suitability_sell_only_violation.json`:
  - `options.enable_suitability_scanner=true`
  - governance scan emits `NEW` issue for blocked BUY attempt in `SELL_ONLY`

## Understanding Output Statuses

* **READY:** All constraints met, trades generated, safety checks passed. Ready for execution.
* **PENDING_REVIEW:** Trades generated but require human approval (e.g., cash drift, soft constraint breach).
* **BLOCKED:** Critical failure (Data Quality, Hard Constraint, Safety Violation). No trades valid.

 
