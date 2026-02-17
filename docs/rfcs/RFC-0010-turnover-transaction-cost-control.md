# RFC-0010: Turnover & Transaction Cost Control

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
| **Created** | 2026-02-17 |
| **Target Release** | TBD |
| **Doc Location** | docs/rfcs/RFC-0010-turnover-transaction-cost-control.md |

---

## 0. Executive Summary

This RFC introduces a turnover budget so the engine can produce best-effort rebalances instead of always forcing full convergence to model targets.

Key outcomes:
1. Add a run-level turnover cap (`max_turnover_pct`).
2. Rank and select trade intents by drift-reduction efficiency.
3. Return explicit diagnostics for dropped intents.

---

## 1. Problem Statement

Full rebalances can produce many low-value trades with high implementation cost (commissions, spreads, market impact). The engine needs a deterministic policy to stop after spending a configured turnover budget.

---

## 2. Goals and Non-Goals

### 2.1 Goals
1. Add `max_turnover_pct` to options.
2. Select a subset of candidate intents when proposed turnover exceeds budget.
3. Preserve deterministic outputs for identical inputs.
4. Expose dropped intents and reason codes.

### 2.2 Non-Goals
1. Partial scaling of a selected intent in this RFC.
2. Explicit spread/impact model calibration by venue.
3. Multi-period turnover planning.

---

## 3. Proposed Implementation

### 3.1 Data Model Changes (`src/core/models.py`)

```python
class EngineOptions(BaseModel):
    max_turnover_pct: Optional[Decimal] = None  # 0 <= value <= 1

class DroppedIntent(BaseModel):
    instrument_id: str
    reason: str  # TURNOVER_LIMIT
    potential_notional: Money
    score: Decimal

class DiagnosticsData(BaseModel):
    dropped_intents: List[DroppedIntent] = Field(default_factory=list)
```

Validation:
1. Reject `max_turnover_pct < 0` or `> 1`.

### 3.2 Intent Selection Logic (`src/core/engine.py`)

Apply in Stage 4 after candidate intent generation.

Algorithm:
1. If `max_turnover_pct` is unset, keep existing behavior.
2. Compute `budget = portfolio_value_base * max_turnover_pct`.
3. Compute `proposed = sum(abs(intent.notional_base.amount))`.
4. If `proposed <= budget`, keep all intents.
5. Else:
   1. Score each candidate:
      1. Primary: absolute drift reduction contributed by intent.
      2. Secondary tie-break: lower notional first (to improve fit).
      3. Final tie-break: instrument_id ascending.
   2. Iterate sorted candidates and include an intent only when `used + notional <= budget`.
   3. Record excluded intents with reason `TURNOVER_LIMIT`.

Rationale:
1. Skip-and-continue behavior is required; do not stop on first oversized trade.
2. This provides a better fill of remaining budget than first-fit stopping.



---

## 4. Test Plan

Add `tests/golden_data/scenario_10_turnover_cap.json`.

Scenario:
1. Portfolio value: 100,000 base currency.
2. Candidate buys: A=10,000, B=10,000, C=2,000.
3. `max_turnover_pct = 0.15` (budget 15,000).

Expected:
1. Proposed turnover 22,000 exceeds budget.
2. Selection uses skip-and-continue.
3. Final intents include A and C (12,000 total), B dropped.
4. Diagnostics include dropped B with reason and score.

Add regression case where exact-fit combination exists and verify deterministic selection.

---

## 5. Rollout and Compatibility

1. Backward compatible with default `max_turnover_pct=None`.
2. Add response warning `PARTIAL_REBALANCE_TURNOVER_LIMIT` when any intent is dropped.

### 5.1 Carry-Forward Requirements from RFC-0001 to RFC-0007A

1. Canonical simulate endpoint remains `POST /rebalance/simulate`.
2. Turnover selection must preserve existing safety/compliance pass in Stage 5 (`NO_SHORTING`, `INSUFFICIENT_CASH`, reconciliation).
3. Non-zero holdings locking (`qty != 0`) from RFC-0007A should be completed before production rollout to avoid selecting intents on incompletely locked books.

---

## 6. Open Questions

1. Should transaction cost estimates be explicit input and merged into scoring now or later?
2. Should partial intent sizing be allowed under a separate flag in a future RFC?

---

## 7. Status and Reason Code Conventions

1. Run status values remain aligned to RFC-0007A: `READY`, `PENDING_REVIEW`, `BLOCKED`.
2. Turnover-limit outcomes remain `READY` when safety checks pass, with warnings/diagnostics attached.
3. This RFC introduces reason and warning codes:
   1. `TURNOVER_LIMIT` (dropped intent reason)
   2. `PARTIAL_REBALANCE_TURNOVER_LIMIT` (result warning code)
