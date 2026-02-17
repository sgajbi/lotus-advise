# RFC-0009: Tax-Aware Rebalancing (HIFO and Tax Budget)

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
| **Created** | 2026-02-17 |
| **Target Release** | TBD |
| **Doc Location** | docs/rfcs/RFC-0009-tax-aware-rebalancing-hifo-tax-budget.md |

---

## 0. Executive Summary

This RFC introduces lot-level selling logic and a run-level capital-gains budget.

Key outcomes:
1. Sell intent generation becomes tax-lot aware.
2. Default lot selection uses HIFO (highest cost first) to reduce gains.
3. The run can enforce `max_realized_capital_gains`, accepting tracking drift when the budget is exhausted.

---

## 1. Problem Statement

Position-level quantity only is not enough for tax-sensitive mandates. A single instrument may contain lots with materially different cost basis. Without explicit lot selection, brokers may apply FIFO and realize avoidable gains.

The engine should produce deterministic sell quantities that are consistent with a declared lot policy and budget.

---

## 2. Goals and Non-Goals

### 2.1 Goals
1. Support optional tax-lot input for positions.
2. Implement HIFO sell allocation.
3. Enforce optional max realized capital gains per run.
4. Report realized gains/losses in result diagnostics.

### 2.2 Non-Goals
1. Jurisdiction-specific tax rules (wash sales, holding period tax rates, exemptions).
2. Tax optimization across multiple accounts.
3. Full tax-lot execution instructions to OMS in this RFC.

---

## 3. Proposed Design

### 3.1 Data Model Changes (`src/core/models.py`)

```python
class TaxLot(BaseModel):
    lot_id: str
    quantity: Decimal
    unit_cost: Money
    purchase_date: str  # ISO date

class Position(BaseModel):
    instrument_id: str
    quantity: Decimal
    market_value: Optional[Money] = None
    lots: List[TaxLot] = Field(default_factory=list)

class EngineOptions(BaseModel):
    max_realized_capital_gains: Optional[Decimal] = None  # base currency amount
```

Validation:
1. `sum(lot.quantity)` must equal `position.quantity` within tolerance when lots are provided.
2. Reject negative lot quantities.

### 3.2 Sell Allocation Logic (`src/core/engine.py`)

Apply this logic in Stage 4 during sell intent generation.

Algorithm:
1. Determine target sell quantity for instrument.
2. Build lot sequence:
   1. If lots provided, sort by `unit_cost desc`, then `purchase_date desc`, then `lot_id asc`.
   2. If lots missing, use legacy synthetic lot (current quantity, average cost if available).
3. Iterate lots and compute per-lot realized PnL:
   1. `gain = (sell_price - lot_cost) * sold_qty`.
   2. If `max_realized_capital_gains` is configured and `accum_gain + gain` exceeds budget:
      1. Reduce `sold_qty` to remaining gain headroom.
      2. Mark reason `TAX_BUDGET_LIMIT_REACHED`.
      3. Stop further sells for that instrument.
4. Emit constrained sell intent quantity.
5. Carry unsatisfied drift forward as accepted residual.

Important edge case:
1. Loss-generating sells (`gain < 0`) always improve budget headroom and are allowed.

### 3.3 Reporting

```python
class TaxImpact(BaseModel):
    total_realized_gain: Money
    total_realized_loss: Money
    budget_limit: Optional[Money] = None
    budget_used: Optional[Money] = None

class RebalanceResult(BaseModel):
    tax_impact: Optional[TaxImpact] = None
```

Diagnostics should include per-instrument constrained sells caused by tax budget.

---

## 4. Test Plan

Add `tests/golden_data/scenario_09_tax_hifo.json`.

Scenario:
1. Position `ABC` has two lots:
   1. 50 @ 10
   2. 50 @ 100
2. Market price is 100.
3. Model implies sell 50.
4. Options: `max_realized_capital_gains = 100`.

Expected:
1. Engine selects high-cost lot first.
2. Sell 50 with realized gain 0.
3. Status `READY`.
4. `tax_impact.total_realized_gain == 0`.

Add second case where requested sell exceeds budget and verify partial sell with diagnostics.

---

## 5. Rollout and Compatibility

1. Backward compatible if `lots` are omitted.
2. Feature is opt-in for budget; HIFO applies only when lots exist.
3. API docs must clarify legacy path versus lot-aware path.

### 5.1 Carry-Forward Requirements from RFC-0001 to RFC-0007A

1. Canonical simulate endpoint remains `POST /rebalance/simulate`.
2. No-short and oversell safeguards remain mandatory (`NO_SHORTING` / `SELL_EXCEEDS_HOLDINGS`) while applying lot-level sell logic.
3. Do not assume persistence-backed idempotency store exists; tax-aware behavior must remain deterministic in stateless runs.

---

## 6. Open Questions

1. Should default lot policy be configurable (`HIFO`, `FIFO`, `LIFO`) now or later?
2. Should tax-budget enforcement be account-level only, or also per-instrument caps?

---

## 7. Status and Reason Code Conventions

1. Run status values remain aligned to RFC-0007A: `READY`, `PENDING_REVIEW`, `BLOCKED`.
2. Tax constraints should not introduce custom status variants; use diagnostics reason codes instead.
3. This RFC introduces reason code:
   1. `TAX_BUDGET_LIMIT_REACHED`
