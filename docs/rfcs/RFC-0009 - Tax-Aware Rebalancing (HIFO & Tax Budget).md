
# RFC-0009: Tax-Aware Rebalancing (HIFO & Tax Budget)

**Status:** DRAFT
**Created:** 2026-02-17
**Depends On:** RFC-0008 (Multi-Dimensional Constraints)

---

## 0. Executive Summary

This RFC introduces tax efficiency into the trade generation process. It allows the engine to be aware of the *cost basis* of the assets it is selling.

**Key Capabilities:**
1.  **Tax Lots:** Input positions can now include specific lots (Purchase Date, Quantity, Cost Basis).
2.  **HIFO Logic:** When selling, the engine automatically selects the "Highest In" (most expensive) lots first to minimize realized gains.
3.  **Tax Budget:** A new option (`max_realized_capital_gains`) stops the engine from selling further if the client's tax liability for the run exceeds a specific threshold.

---

## 1. Problem Statement

Currently, the engine views a position like `100 units of AAPL` as a single blob.
* **Scenario:** The model asks to sell 50 units.
* **Reality:** The client bought 50 units at $10 (Low Cost) and 50 units at $150 (High Cost).
* **Current Behavior:** The engine just says "Sell 50". The broker might default to FIFO (First In, First Out), selling the $10 lots and triggering a massive taxable gain ($140 profit per share).
* **Desired Behavior:** The engine should explicitly instruct (or simulate) selling the $150 lots first, resulting in zero gain (or a loss).

---

## 2. Goals

### 2.1 Functional Requirements
* **Data Model:** Expand `Position` to support a list of `TaxLot` objects.
* **Logic (HIFO):**
    * Sort lots by `unit_cost` (Descending).
    * Deplete high-cost lots first when fulfilling a sell intent.
* **Constraint (Tax Budget):**
    * Track `accumulated_realized_gains` during the run.
    * If a proposed sell trade pushes `accumulated_gains > max_realized_capital_gains`:
        * **Cap the trade:** Only sell enough to hit the limit, then stop.
        * **Accept Drift:** Leave the remaining position held, even if it violates the Model Weight.

---

## 3. Proposed Implementation

### 3.1 Data Model Changes (`src/core/models.py`)

**1. Define `TaxLot`**
```python
class TaxLot(BaseModel):
    lot_id: str
    quantity: Decimal
    unit_cost: Money  # The price paid per share
    purchase_date: str # ISO Date YYYY-MM-DD

```

**2. Update `Position**`
Add optional lots. If `lots` are missing, we assume `average_cost` (Legacy mode).

```python
class Position(BaseModel):
    instrument_id: str
    quantity: Decimal
    market_value: Optional[Money] = None
    # NEW: Granular tax data
    lots: List[TaxLot] = Field(default_factory=list)

```

**3. Update `EngineOptions**`
Add the budget.

```python
class EngineOptions(BaseModel):
    # ... existing fields ...
    
    # NEW: Max allowed capital gains for this run (in Base Currency)
    max_realized_capital_gains: Optional[Decimal] = None 

```

### 3.2 Logic Changes (`src/core/engine.py`)

**Modify `_generate_intents` (Stage 4):**

Currently, we calculate `qty = target - current`. We must refine the **Sell** logic.

**Algorithm (Tax Aware Sell):**

1. **Calculate Target Sell Qty:** e.g., Need to sell 50 units.
2. **Get Lots:** Retrieve `lots` for the position. Sort by `unit_cost` DESC (HIFO).
3. **Simulate Sales:**
* Iterate through lots.
* Calculate `Gain = (Current_Price - Lot_Cost) * Lot_Qty`.
* **Check Budget:**
* If `Total_Gains + Gain > max_realized_capital_gains`:
* Reduce `Lot_Qty` to fit the budget.
* Stop selling after this lot (Constraint Hit).


* Else:
* Sell full `Lot_Qty`.
* Add to `Total_Gains`.






4. **Generate Intent:** Create the `SecurityTradeIntent` with the *constrained* quantity.

### 3.3 Reporting (`src/core/models.py`)

We should output the tax impact in the result.

```python
class TaxImpact(BaseModel):
    total_realized_gain: Money
    total_realized_loss: Money

class RebalanceResult(BaseModel):
    # ...
    tax_impact: Optional[TaxImpact] = None

```

---

## 4. Test Plan (Golden Scenarios)

We will create `tests/golden_data/scenario_09_tax_hifo.json`.

**Scenario:**

* **Holdings:** 100 units of `ABC`.
* Lot 1: 50 units @ $10 (Bought long ago).
* Lot 2: 50 units @ $100 (Bought recently).


* **Market Price:** $100.
* **Model:** Sell 50 units (Target 0%).
* **Options:** `max_realized_capital_gains`: $100.

**Logic Check:**

* **FIFO (Bad):** Sell Lot 1 ($10). Gain = ($100 - $10) * 50 = $4,500. **Breaches Budget.**
* **HIFO (Good):** Sell Lot 2 ($100). Gain = ($100 - $100) * 50 = $0. **Passes.**

**Expected Outcome:**

* Trade: SELL 50 units.
* Logic: Engine implicitly selected Lot 2.
* Tax Impact: $0.00.
* Status: `READY`.

```

```