# RFC-0014C: Drift Analytics for Advisory Proposals (Before vs After vs Reference Model)

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-18 |
| **Target Release** | MVP-14C |
| **Depends On** | RFC-0014A (Proposal Simulation), RFC-0006A (After-state completeness) |
| **Optional Depends On** | RFC-0014B (Auto-funding) — not required for drift math, but improves realism |
| **Doc Location** | `docs/rfcs/advisory pack/refine/RFC-0014C-drift-analytics.md` |
| **Backward Compatibility** | Not required |
| **Implemented In** | 2026-02-19 |

---

## 0. Executive Summary

RFC-0014C adds **drift analytics** to the advisory proposal workflow to quantify:

- how far the **current portfolio** is from a **reference target model** (Before drift)
- how far the **simulated proposal** is from that model (After drift)
- how much drift is **improved / worsened** by the proposal (Delta)

This provides the advisor-facing narrative: *“This proposal reduces your portfolio drift from X% to Y% and fixes the biggest misalignments.”*

This RFC is purely analytics (no persistence). It assumes you already return complete before/after allocations.

---

## 1. Motivation / Problem Statement

Advisory proposals are not only about “what trades happen” — the advisor must justify:

- **Why these trades are sensible**
- **What portfolio problem they fix**
- **How much alignment improves** against the intended mandate/model

Your draft RFC-0014 implies that the proposal engine should help advisors communicate outcomes, not only simulate trades. Drift analytics is the cleanest first step toward an “advisory-ready” proposal story. 

---

## 2. Scope

### 2.1 In Scope
- Add `drift_analysis` to proposal simulation response.
- Support drift comparison against a **reference target model**.
- Provide both:
  - **asset-class drift**
  - **instrument drift** (for instruments present in universe/holdings/targets)
- Provide “top contributors” lists for advisor narrative.

### 2.2 Out of Scope
- Portfolio optimization / generating new targets (already bypassed in proposal flow)
- Tracking drift over time
- Multi-level models (region/sector/style) — can be added later
- Risk-based drift (tracking error, active risk) — later RFC

---

## 3. Definitions

### 3.1 Weights
- All drift computations use **weights in portfolio base currency**.
- Weights derived from:
  - `before.allocation_by_*`
  - `after_simulated.allocation_by_*`

### 3.2 Reference Model
Reference model is an input structure representing desired weights.

Two levels supported:
1) Asset class targets (required)
2) Instrument targets (optional)

**ReferenceModel** example:
```json
{
  "model_id": "mdl_balanced_60_40",
  "as_of": "2026-02-18",
  "base_currency": "SGD",
  "asset_class_targets": [
    { "asset_class": "EQUITY", "weight": "0.60" },
    { "asset_class": "FIXED_INCOME", "weight": "0.35" },
    { "asset_class": "CASH", "weight": "0.05" }
  ],
  "instrument_targets": [
    { "instrument_id": "US_EQ_ETF", "weight": "0.20" },
    { "instrument_id": "SG_BOND_ETF", "weight": "0.15" }
  ]
}
````

---

## 4. API Changes

### 4.1 Request

Extend `POST /rebalance/proposals/simulate` request with optional:

* `reference_model` (object)
* or `reference_model_id` (string) if you already have a lookup mechanism (not recommended without persistence/connector; for MVP use inline object)

For MVP:

* **inline `reference_model` only** (deterministic, testable)

### 4.2 Response

Add:

```json
"drift_analysis": {
  "reference_model": { "model_id": "...", "as_of": "..." },
  "asset_class": { ... },
  "instrument": { ... }
}
```

If no reference model provided:

* omit `drift_analysis` entirely (or include it with `status="NOT_PROVIDED"`)

---

## 5. Drift Metrics (Institution-grade but simple)

### 5.1 Primary metric: Total Drift (L1 / Manhattan distance)

For a set of buckets `i` (asset classes or instruments), define:

* `drift_total = 0.5 * Σ | w_portfolio(i) - w_model(i) |`

This yields a value in `[0, 1]`, interpretable as “percentage misalignment”.
Example: 0.12 means “12% drift”.

Why 0.5 factor:

* ensures drift is not double-counted (standard in portfolio drift/active share style metrics).

### 5.2 Bucket drift details

For each bucket:

* `portfolio_weight_before`
* `portfolio_weight_after`
* `model_weight`
* `drift_before = portfolio_weight_before - model_weight`
* `drift_after  = portfolio_weight_after  - model_weight`
* `abs_drift_before`, `abs_drift_after`
* `improvement = abs_drift_before - abs_drift_after`

### 5.3 Coverage / bucket universe rules

To be deterministic and auditable, define the bucket set explicitly:

#### Asset class drift buckets:

* Use all asset classes present in:

  * model.asset_class_targets
  * before allocation
  * after allocation
    Always include `CASH`.

If an asset class exists in portfolio but not in model:

* treat model_weight = 0.0 and include as bucket (this is important to surface “unmodeled exposure”).

#### Instrument drift buckets (optional):

If `reference_model.instrument_targets` is present:

* bucket set = union of:

  * model instruments
  * instruments held before
  * instruments held after
  * instruments traded in intents
    For instruments not in model, model_weight = 0.

This prevents “hiding” drift from new instruments introduced by proposals.

---

## 6. Output Schema (Detailed)

### 6.1 Asset class drift output

```json
"asset_class": {
  "drift_total_before": "0.1200",
  "drift_total_after": "0.0700",
  "drift_total_delta": "-0.0500",
  "top_contributors_before": [
    {
      "bucket": "EQUITY",
      "model_weight": "0.60",
      "portfolio_weight_before": "0.72",
      "portfolio_weight_after": "0.65",
      "abs_drift_before": "0.12",
      "abs_drift_after": "0.05",
      "improvement": "0.07"
    }
  ],
  "buckets": [ ...same objects for every asset class... ]
}
```

### 6.2 Instrument drift output

Same structure, where `bucket = instrument_id`.

---

## 7. Narrative helpers (Advisory-friendly)

Add short “highlights” fields (machine-generated but deterministic):

* `highlights`:

  * `largest_improvements[]`
  * `largest_deteriorations[]`
  * `unmodeled_exposures[]` (portfolio exposure where model weight=0 above threshold)

These are not “LLM text”; they are structured facts an advisor UI can render.

---

## 8. Implementation Plan

1. Add `ReferenceModel` and drift output models under `src/core/models.py` (Pydantic v2, decimals)
2. Add drift analytics module at `src/core/common/drift_analytics.py`:

   * method: `compute_drift_analysis(...)` with asset-class and optional instrument dimensions
3. Ensure allocation inputs are taken from:

   * `before.allocation_by_asset_class`
   * `after_simulated.allocation_by_asset_class`
     and similarly for instruments.
4. Add output wiring in proposal response builder
   * `src/core/advisory/engine.py`
   * `src/api/main.py`
5. Add tests + goldens

---

## 9. Testing Plan

### 9.1 Unit tests

* Drift totals computed correctly with Decimal precision
* Bucket union logic correct:

  * model-only bucket
  * portfolio-only bucket
* Improvement signs correct

### 9.2 Golden tests

Add:

* `scenario_14C_drift_asset_class.json` (only asset-class model targets)
* `scenario_14C_drift_instrument.json` (instrument targets present)

Each golden asserts:

* drift_total_before/after/delta
* top contributors ordering deterministic (sort by abs_drift_before desc, then bucket id asc)

---

## 10. Acceptance Criteria (DoD)

* If `reference_model` provided, response contains `drift_analysis`.
* Drift totals follow: `0.5 * sum(abs diff))` and match golden outputs.
* Drift buckets include unmodeled exposures (model_weight=0) deterministically.
* Top contributors are deterministic and correctly show improvements/deteriorations.
* No floats used; all Decimal strings.
* Goldens cover both asset-class and instrument drift.

---

## 11. Follow-ups

* RFC-0014D: Suitability Scanner v1 (new/resolved/persistent)
* RFC-0014E: Proposal Artifact packaging (client-ready report bundle)
* RFC-0014F: Workflow gating (PENDING_REVIEW triggers)




