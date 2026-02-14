# DPM Rebalance Engine - Demo Pack

This folder contains curated scenarios to demonstrate the **Institutional Capabilities** of the engine.

## How to Run
Use the `update_goldens.py` script to generate the latest JSON outputs, or inspect `tests/golden_data/` for the actual files.

## Scenario Highlights

### 1. Drift Rebalance (Scenario 101)
* **Context:** A standard portfolio (Cash + Equity) that has drifted from its target.
* **Action:** The engine sells the overweight asset and buys the underweight asset.
* **Feature:** Shows `SECURITY_TRADE` generation with correct `SELL` -> `BUY` ordering.

### 2. Multi-Currency FX Funding (Scenario 104)
* **Context:** An SGD-base portfolio buying a USD asset.
* **Action:** The engine generates an `FX_SPOT` trade (Buy USD / Sell SGD) to fund the purchase.
* **Feature:** Shows **Hub-and-Spoke FX** and dependency linking (Security Trade depends on FX Trade).

### 3. Sell-Only Liquidation (Scenario 105)
* **Context:** Client holds an asset marked `SELL_ONLY` on the product shelf.
* **Action:** Engine blocks any new buys for this asset. Since the target model requested 50%, the engine forces the target to 0% and redistributes the weight to valid assets.
* **Feature:** Shows `SHELF_STATUS_SELL_ONLY_BUY_BLOCKED` logic and redistribution.

### 4. Dust Suppression (Scenario 110)
* **Context:** A tiny allocation (1%) results in a trade below the Minimum Trade Size ($500).
* **Action:** The engine calculates the trade but suppresses it from the final list.
* **Feature:** Shows `diagnostics.suppressed_intents` and clean output.