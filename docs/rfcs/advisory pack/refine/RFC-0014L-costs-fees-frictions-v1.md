# RFC-0014L: Cost, Fees, and Transaction Frictions v1 (Net-of-Cost Proposal Simulation)

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
| **Created** | 2026-02-18 |
| **Target Release** | MVP-14L |
| **Depends On** | RFC-0014A (Proposal Simulation), RFC-0014B (Auto-funding) |
| **Strongly Recommended** | RFC-0014E (Proposal Artifact), RFC-0014K (DQ + Lineage) |
| **Doc Location** | `docs/rfcs/advisory pack/refine/RFC-0014L-costs-fees-frictions-v1.md` |
| **Backward Compatibility** | Not required |

---

## 0. Executive Summary

RFC-0014L adds **transaction frictions** so advisory proposals reflect more realistic outcomes:

- trading commissions / brokerage
- stamp duties / levies (simple jurisdiction rules)
- FX spread / markup
- minimum fees
- estimated slippage (bps)
- cash impact and after-state computed **net of costs**

The goal is not perfect TCA; it is a deterministic, explainable **cost estimate** that improves proposal credibility and helps advisors explain expected impacts to clients.

---

## 1. Motivation / Problem Statement

Advisory proposals that ignore costs can be misleading:
- cash after-state is overstated
- small rebalances may not be worth executing after fees
- FX conversions can incur meaningful spreads

Institutions require at least a v1 cost model for proposal artifacts:
- “Estimated total cost of implementation”
- “Estimated cash impact by currency”
- “Cost breakdown per trade”

---

## 2. Scope

### 2.1 In Scope (v1)
- Add cost estimation engine:
  - per security trade costs
  - per FX trade costs
- Apply estimated costs to:
  - cash ledger updates
  - after-state valuation
- Expose cost breakdown in:
  - proposal simulate response
  - proposal artifact

### 2.2 Out of Scope (v1)
- Tax (capital gains, withholding)
- Market impact models
- Venue-specific fee schedules
- Complex derivatives pricing costs
- Performance attribution net-of-fees (later RFC)

---

## 3. Inputs / Config

Costs must be driven by **Policy Packs** (RFC-0014H) and/or request options.

### 3.1 CostPolicy schema (policy pack section)
```json
"cost_policy": {
  "security_trade": {
    "default_commission_bps": "5",
    "min_fee_by_currency": { "USD": "5.00", "SGD": "5.00" },
    "stamp_duty_rules": [
      { "jurisdiction": "SG", "asset_class": "EQUITY", "bps": "0" }
    ],
    "slippage_bps_default": "10"
  },
  "fx_trade": {
    "spread_bps_default": "10",
    "min_fee_by_currency": { "SGD": "0.00" }
  }
}
````

### 3.2 Request override options (optional)

```json
"options": {
  "include_costs": true,
  "cost_overrides": {
    "slippage_bps": "15",
    "fx_spread_bps": "12"
  }
}
```

Defaults:

* `include_costs=false` unless enabled by policy pack (institution-specific decision)
* When enabled, all calculations must be deterministic.

---

## 4. Cost Model (Deterministic)

### 4.1 Security trade estimated notional

For trade in currency `CCY`:

* `notional = quantity * price` (or provided notional)
* `notional_base` computed using FX (from market snapshot)

### 4.2 Commission

* `commission = max(min_fee_ccy, notional * commission_bps / 10_000)`

### 4.3 Stamp duty / levy (simple rules)

Apply based on:

* jurisdiction
* asset_class or product_type
* side (often BUY only)

v1:

* implement a rule table look-up; if no rule -> 0.

### 4.4 Slippage

Estimated execution friction:

* `slippage_cost = notional * slippage_bps / 10_000`

You may choose to model slippage as:

* additional cash cost for BUY
* reduced proceeds for SELL

Deterministic convention (recommended):

* BUY: increase cash outflow by slippage_cost
* SELL: decrease cash inflow by slippage_cost

### 4.5 FX spread / markup

For FX intent:

* if pair is `BUY/SELL`, base rate = market rate
* effective rate includes spread:

  * BUY currency becomes slightly more expensive:
  * `effective_rate = market_rate * (1 + spread_bps/10_000)`
* `sell_amount = buy_amount * effective_rate`
* FX fee can also be modeled as explicit fee line item (optional)

---

## 5. Applying Costs to Simulation

### 5.1 Ledger application order

Costs must follow the same deterministic ordering:

* CASH_FLOW → SELL → FX → BUY

When applying each intent:

* compute its cost lines
* adjust cash ledger accordingly
* record cost lines in output

### 5.2 Output: cost breakdown

Add:

```json
"costs": {
  "total_estimated_base": { "amount": "123.45", "currency": "SGD" },
  "by_currency": [
    { "currency": "USD", "amount": "15.00" },
    { "currency": "SGD", "amount": "108.45" }
  ],
  "line_items": [
    {
      "intent_id": "oi_...",
      "type": "SECURITY_TRADE",
      "currency": "USD",
      "commission": "5.00",
      "stamp_duty": "0.00",
      "slippage": "10.00",
      "total": "15.00",
      "total_base": "20.25"
    }
  ],
  "assumptions": {
    "commission_bps": "5",
    "slippage_bps": "10",
    "fx_spread_bps": "10"
  }
}
```

### 5.3 Proposal Artifact integration

In RFC-0014E artifact:

* include “Estimated implementation cost” section
* include per-trade cost disclosure in trade list
* include assumptions in `assumptions_and_limits`

---

## 6. Edge Cases

* If missing price: cost calculation cannot proceed → follow DQ policy (often block)
* If notional too small: min fee dominates; highlight this in line item
* If partial fills: post-trade reconciliation (RFC-0014J) should compare expected vs realized costs later

---

## 7. Implementation Plan

1. Add `CostPolicy` models and load from policy pack
2. Implement `CostEngine`:

   * `estimate_security_trade_cost(trade, price, policy)`
   * `estimate_fx_cost(fx_intent, rate, policy)`
3. Wire cost engine into simulation pipeline:

   * compute and apply costs during ledger updates
4. Add output section `costs` to proposal result
5. Update artifact builder to include cost sections
6. Add tests + goldens

---

## 8. Testing Plan

Unit tests:

* commission bps + min fee logic
* slippage applied buy vs sell correctly
* FX spread increases sell amount deterministically
* multi-currency totals reconcile

Golden tests:

* `scenario_14L_costs_basic.json`
* `scenario_14L_costs_min_fee_dominates.json`
* `scenario_14L_fx_spread_cost.json`

Each asserts:

* costs.total_estimated_base
* per-line breakdown stability
* after-state cash reduced net of costs

---

## 9. Acceptance Criteria (DoD)

* When `include_costs=true`, proposal simulation output includes deterministic `costs` block.
* Cash ledger and after-state reflect net-of-cost impacts.
* Proposal artifact includes cost summary and assumptions.
* Goldens cover security + FX costs and min fee behavior.

---

## 10. Follow-ups

* Management fees and retrocessions modeling
* Custody fees
* Performance net-of-fees reporting
* TCA and realized cost comparison using fills (RFC-0014J)

 



