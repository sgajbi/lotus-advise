# RFC-0011: Settlement Awareness (Cash Ladder & Overdraft Protection)

**Status:** DRAFT
**Created:** 2026-02-17
**Depends On:** RFC-0007A (Contract Tightening)

---

## 0. Executive Summary

This RFC introduces **Time** as a constraint. It prevents the engine from assuming that cash generated from a sale is immediately available for a purchase if the settlement cycles do not align.

**Key Capabilities:**
1.  **Settlement Config:** `ShelfEntry` now defines settlement latency (e.g., `T+1`, `T+2`).
2.  **Cash Ladder:** The engine projects cash balances day-by-day (T+0 to T+5).
3.  **Overdraft Blocking:** A run is `BLOCKED` if the projected cash balance drops below zero on any specific future date, even if the *final* net position is positive.

---

## 1. Problem Statement

Currently, the engine treats all cash as "Instant."
* **Scenario:**
    * **Sell:** $1M of `Global_Fund_A` (Settles **T+3**).
    * **Buy:** $1M of `US_Tech_Stock` (Settles **T+1**).
* **Current Logic:** $+1M - 1M = 0$. The engine thinks this is fine.
* **Reality:**
    * **T+1:** You must pay for the Tech Stock. You have $0 (Fund money hasn't arrived). **Overdraft!**
    * **T+3:** Fund money arrives. You are back to $0.
* **Consequence:** The client incurs overdraft interest or the trade fails settlement.

---

## 2. Goals

### 2.1 Functional Requirements
* **Data Model:** Add `settlement_days` (integer) to `ShelfEntry`.
* **Logic (Cash Ladder):**
    * In **Stage 5 (Simulation)**, instead of just summing totals, distribute cash impacts across a timeline.
    * `Cash_T0`, `Cash_T1`, `Cash_T2`...
    * Check `INSUFFICIENT_CASH` for *each* bucket.
* **Safety:** If `Cash_Tn < 0`, block the run (unless an overdraft facility is configured).

---

## 3. Proposed Implementation

### 3.1 Data Model Changes (`src/core/models.py`)

**1. Update `ShelfEntry`**

```python
class ShelfEntry(BaseModel):
    instrument_id: str
    # ...
    # NEW: Days to settle. 0=Instant, 1=T+1, 2=T+2
    settlement_days: int = Field(default=2) 

```

**2. Update `DiagnosticsData**`
Add the ladder for debugging.

```python
class CashLadderPoint(BaseModel):
    date_offset: int  # 0, 1, 2...
    currency: str
    projected_balance: Decimal

class DiagnosticsData(BaseModel):
    # ...
    cash_ladder: List[CashLadderPoint] = Field(default_factory=list)

```

### 3.2 Logic Changes (`src/core/engine.py`)

**Modify `_generate_fx_and_simulate` (Stage 5):**

Currently, we just do `g_cash(after, ccy).amount += delta`. We need to simulate the timing.

**Algorithm:**

1. **Initialize Ladder:** Create a map `Ladder[Currency][Day]`. Initialize with current `settled_cash`.
2. **Map Trades to Days:**
* Iterate through `intents`.
* Lookup `settlement_days` for the instrument.
* **Buy:** `Ladder[Ccy][SettleDay] -= Notional`.
* **Sell:** `Ladder[Ccy][SettleDay] += Notional`.
* **FX:** Usually T+2.
* `Ladder[BuyCcy][2] += Amount`.
* `Ladder[SellCcy][2] -= Amount`.




3. **Running Sum:**
* For each currency, calculate the cumulative balance for T+0, T+1, T+2...
* `Balance_T1 = Balance_T0 + Net_Flow_T1`.


4. **Validate:**
* If `Balance_Tn < 0` for any `n`:
* Return `BLOCKED`.
* Reason: `OVERDRAFT_ON_T_PLUS_{n}`.





---

## 4. Test Plan (Golden Scenarios)

We will create `tests/golden_data/scenario_11_settlement_fail.json`.

**Scenario:**

* **Cash:** $0.
* **Holdings:** $100k in `Slow_Fund` (T+3).
* **Model:** Sell `Slow_Fund`, Buy `Fast_Stock` (T+1).

**Logic Check:**

* **T+1:** Buy `Fast_Stock` requires $100k. Cash available: $0. **Balance: -$100k.**
* **T+2:** Balance -$100k.
* **T+3:** Sell `Slow_Fund` settles (+$100k). Balance: $0.

**Expected Outcome:**

* **Status:** `BLOCKED`.
* **Diagnostics:** `cash_ladder` shows negative balance at T+1 and T+2.
* **Remediation:** The user must manually execute the Sell first, wait 3 days, then run the engine again to Buy (or enable an overdraft flag).

```

```