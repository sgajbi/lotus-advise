# RFC-0010: Turnover & Transaction Cost Control

**Status:** DRAFT
**Created:** 2026-02-17
**Depends On:** RFC-0007A (Contract Tightening)

---

## 0. Executive Summary

This RFC introduces a **Turnover Budget** to the rebalancing process. It transforms the engine from an "All or Nothing" calculator into a "Best Effort" optimizer.

**Key Capabilities:**
1.  **Turnover Cap:** A new option (`max_turnover_pct`) limits the total value of trades generated in a single run (e.g., "Do not trade more than 5% of the portfolio value").
2.  **Efficiency Ranking:** When the cap is hit, the engine prioritizes trades that reduce the most Tracking Error (Drift) and discards low-impact "noise" trades.

---

## 1. Problem Statement

Currently, the engine is dogmatic: if the Model Portfolio changes by 50%, the engine generates trades to turnover 50% of the portfolio.
* **Scenario:** A tactical model update changes 100 small positions by 0.1% each.
* **Consequence:** The engine generates 100 small trades.
* **Cost:** Broker commissions and bid-ask spreads eat up the theoretical alpha.
* **Desired Behavior:** The engine should only execute the "highest impact" trades up to a specific budget (e.g., 5% turnover) and ignore the rest.

---

## 2. Goals

### 2.1 Functional Requirements
* **Configuration:** Add `max_turnover_pct` to `EngineOptions`.
* **Logic (Greedy Selection):**
    * Generate all *potential* trades (Stage 4).
    * Calculate the total proposed turnover.
    * If `Total > Limit`:
        * Sort trades by "Impact" (Contribution to drift reduction).
        * Accept trades until the limit is reached.
        * Discard the remaining trades.
* **Reporting:** Flag that the result is `PARTIAL_REBALANCE` due to turnover constraints.

---

## 3. Proposed Implementation

### 3.1 Data Model Changes (`src/core/models.py`)

**1. Update `EngineOptions`**

```python
class EngineOptions(BaseModel):
    # ... existing fields ...

    # NEW: Max turnover as a fraction of total portfolio value (e.g., 0.05 = 5%)
    max_turnover_pct: Optional[Decimal] = None

```

**2. Update `DiagnosticsData**`
Add a field to track dropped trades.

```python
class DroppedIntent(BaseModel):
    instrument_id: str
    reason: str  # e.g., "TURNOVER_LIMIT"
    potential_notional: Money

class DiagnosticsData(BaseModel):
    # ...
    dropped_intents: List[DroppedIntent] = Field(default_factory=list)

```

### 3.2 Logic Changes (`src/core/engine.py`)

**Modify `_generate_intents` (Stage 4):**

We inject a **Selection Step** before returning the list of intents.

**Algorithm:**

1. **Generate Candidates:** Create all `SecurityTradeIntent` objects as usual (based on Target vs. Current).
2. **Calculate Total Budget:** `Budget = Total_Portfolio_Value * max_turnover_pct`.
3. **Check Usage:** `Proposed_Turnover = Sum(abs(i.notional_base) for i in candidates)`.
4. **Optimization Loop (If `Proposed > Budget`):**
* **Score Candidates:**
* Score = `abs(Target_Weight - Current_Weight)`. (The larger the drift being fixed, the higher the score).


* **Sort:** Descending order of Score.
* **Select:** Iterate through sorted list:
* If `Used + Trade_Value <= Budget`:
* Keep Trade.
* `Used += Trade_Value`.


* Else:
* Drop Trade (Add to `diagnostics.dropped_intents`).




* *Note:* We do not "scale down" trades (partial fills) in this MVP, as that creates odd-lot complexity. We simply drop the least important ones.



---

## 4. Test Plan (Golden Scenarios)

We will create `tests/golden_data/scenario_10_turnover_cap.json`.

**Scenario:**

* **Portfolio:** $100k Cash.
* **Model:**
* Asset A: 10% (Buy $10k)
* Asset B: 10% (Buy $10k)
* Asset C: 2%  (Buy $2k)


* **Options:** `max_turnover_pct`: 0.15 (15% or $15k limit).

**Logic Check:**

* **Proposed:** Buy A ($10k) + Buy B ($10k) + Buy C ($2k) = $22k.
* **Limit:** $15k.
* **Sorting:** A and B have score 0.10. C has score 0.02.
* **Selection:**
1. Pick A ($10k). Used $10k. Remainder $5k.
2. Pick B ($10k). **Fails** ($10k > $5k). Drop B?
* *Refinement:* A greedy algorithm might skip B and try C. Or strictly stop. For MVP, we stop or skip. Let's assume **Skip** logic (try to fit smaller rocks).


3. Pick C ($2k). Fits. Used $12k.



**Expected Outcome:**

* **Intents:** BUY A ($10k), BUY C ($2k). (B is dropped).
* **Diagnostics:** `dropped_intents` contains B.
* **Status:** `READY` (but with warnings).

```

```