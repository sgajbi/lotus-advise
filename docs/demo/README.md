# DPM Rebalance Engine Demo Scenarios

This folder contains JSON input files demonstrating key capabilities of the DPM Rebalance Engine (RFC-0006B). Run these scenarios through the API endpoint.

## Running Scenarios

### API Usage

POST the content of any JSON file to `/rebalance/simulate` with `Idempotency-Key`.

Example:
```bash
curl -X POST "http://127.0.0.1:8000/rebalance/simulate" -H "Content-Type: application/json" -H "Idempotency-Key: demo-01" --data-binary "@docs/demo/01_standard_drift.json"
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

## Understanding Output Statuses

* **READY:** All constraints met, trades generated, safety checks passed. Ready for execution.
* **PENDING_REVIEW:** Trades generated but require human approval (e.g., cash drift, soft constraint breach).
* **BLOCKED:** Critical failure (Data Quality, Hard Constraint, Safety Violation). No trades valid.

 
