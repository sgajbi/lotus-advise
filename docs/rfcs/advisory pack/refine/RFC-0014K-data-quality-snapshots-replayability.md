# RFC-0014K: Data Quality, Snapshots & Replayability (Institution-Grade Determinism)

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
| **Created** | 2026-02-18 |
| **Target Release** | MVP-14K |
| **Depends On** | RFC-0014A (Proposal Simulation) |
| **Strongly Recommended** | RFC-0014E (Proposal Artifact), RFC-0014G (Persistence), RFC-0014H (Policy Packs) |
| **Doc Location** | `docs/rfcs/advisory pack/refine/RFC-0014K-data-quality-snapshots-replayability.md` |
| **Backward Compatibility** | Not required |

---

## 0. Executive Summary

RFC-0014K makes the system **institution-grade** by formalizing:

- **Snapshot contracts** (portfolio, prices, FX, shelf)
- **Data Quality (DQ) policy**: what is required vs optional
- **Replayability / reproducibility** guarantees via canonical hashing and snapshot lineage
- **DQ scoring + diagnostics** so every proposal clearly states its data confidence level
- Standard behavior for **missing prices/FX**, stale timestamps, inconsistent currencies, and incomplete coverage

This RFC is the “truth layer” that prevents the engine from producing plausible but unverifiable outputs.

---

## 1. Motivation / Problem Statement

In real private banking systems:
- portfolio snapshots can be partial or stale,
- market data can be incomplete,
- FX can be missing or inconsistent across pairs,
- product governance data can lag.

If the engine silently proceeds, you get:
- proposals that cannot be executed,
- audit failure (“how did you calculate this?”),
- inconsistent outputs over time.

This RFC ensures every output is:
- reproducible,
- evidence-backed,
- and explicitly labeled with data confidence.

---

## 2. Scope

### 2.1 In Scope
- Define snapshot schemas with `snapshot_id`, `as_of`, and `source` metadata.
- Define DQ policy and enforcement:
  - missing prices / FX
  - missing instrument currency
  - missing issuer_id / liquidity_tier (for suitability)
  - stale market data
  - inconsistent base currency conversions
- Add canonical **Request Hash** and **Snapshot Hash** computation rules.
- Add **Replay Mode**: run engine in “replay” using stored evidence bundle and require identical results.

### 2.2 Out of Scope
- Building a full data platform (ingestion pipelines, real-time feeds)
- Vendor-specific data mapping (Bloomberg/Reuters etc.)
- Mastering instrument reference data in this RFC (only interfaces)

---

## 3. Snapshot Contracts

### 3.1 Common Snapshot Header
All snapshots MUST include:
```json
{
  "snapshot_id": "md_20260218_001",
  "as_of": "2026-02-18T08:00:00Z",
  "source": "VENDOR_X|INTERNAL_Y",
  "schema_version": "1.0.0"
}
````

### 3.2 Portfolio Snapshot

Add/require:

* `portfolio_id`
* `base_currency`
* `positions[]` with `instrument_id`, `quantity`, and **instrument_currency**
* `cash_balances[]` with `currency`, `amount`
* Optional:

  * `tax_lots[]` (later)
  * `accounts[]` (multi-entity later)

DQ requirements:

* `instrument_currency` is REQUIRED for positions (or derivable from shelf/instrument master; if not, DQ fail)
* `base_currency` must be a valid currency code

### 3.3 Market Data Snapshot

Must include:

* `prices[]`: instrument_id, price, currency
* `fx_rates[]`: pair, rate, as_of (optional per-rate)

DQ requirements:

* every traded/held instrument requires a price
* every required conversion requires an FX rate (direct or invertible)
* prices/FX must not be stale beyond policy threshold

### 3.4 Shelf Snapshot (Product Governance)

Must include:

* `instrument_id`, `status`, `asset_class`, `currency`
* optional but recommended (needed for suitability):

  * `issuer_id`
  * `liquidity_tier`
  * `product_type`

---

## 4. Data Quality Policy (Config-Driven)

DQ policy belongs in Policy Pack (RFC-0014H), but this RFC defines baseline defaults.

### 4.1 Required vs Optional data

Required for simulation correctness:

* prices for all held/traded instruments
* FX rates for all required conversions (including funding FX)
* instrument currency for all positions/trades

Required for suitability (if enabled):

* issuer_id
* liquidity_tier
* governance status

Optional:

* sector/region classifications
* risk rating
* document references

### 4.2 Staleness rules

Define a maximum staleness in minutes:

* prices_max_age_minutes = 1440 (1 day) default
* fx_max_age_minutes = 1440 default

If snapshot `as_of` older than threshold:

* if `block_on_stale_market_data=true` → BLOCKED
* else → PENDING_REVIEW + diagnostics

---

## 5. DQ Scoring & Diagnostics

### 5.1 DQ Report schema

Add to response:

```json
"data_quality": {
  "overall": {
    "score": "0.92",
    "grade": "A|B|C|D",
    "blocking": false
  },
  "coverage": {
    "price_coverage_pct": "0.98",
    "fx_coverage_pct": "1.00",
    "shelf_enrichment_pct": "0.85"
  },
  "issues": [
    {
      "dq_code": "MISSING_PRICE",
      "severity": "HIGH",
      "entity": { "instrument_id": "ABC" },
      "message": "No price found for ABC in market snapshot."
    }
  ]
}
```

### 5.2 Scoring rules (deterministic)

* Start score = 1.00
* Deduct fixed penalties per issue type:

  * missing price: -0.20 (HIGH)
  * missing FX: -0.20 (HIGH)
  * stale prices: -0.10 (MEDIUM)
  * missing issuer_id: -0.05 (LOW/MEDIUM depending on suitability enabled)
* Clamp score to [0,1]
* Grade mapping:

  * A: ≥0.95
  * B: ≥0.85
  * C: ≥0.70
  * D: <0.70

Policy packs may override penalties and thresholds.

---

## 6. Canonical Hashing & Lineage

### 6.1 Canonical Request Hash

Compute sha256 over canonical JSON serialization of:

* proposal request body
* excluding volatile fields (e.g., comments)
* sorted keys
* normalized decimals

Store/return:

* `request_hash = "sha256:<hex>"`

### 6.2 Snapshot Hashes

Compute hashes for each snapshot:

* portfolio_snapshot_hash
* market_data_snapshot_hash
* shelf_snapshot_hash

### 6.3 Lineage block (mandatory)

```json
"lineage": {
  "request_hash": "sha256:...",
  "snapshots": {
    "portfolio": { "snapshot_id": "...", "as_of": "...", "hash": "sha256:..." },
    "market_data": { "snapshot_id": "...", "as_of": "...", "hash": "sha256:..." },
    "shelf": { "snapshot_id": "...", "as_of": "...", "hash": "sha256:..." }
  },
  "engine_version": "..."
}
```

---

## 7. Replay Mode (Reproducibility)

### 7.1 API

`POST /rebalance/proposals/replay`

Body:

* `evidence_bundle` (stored from ProposalArtifact / persistence)

Behavior:

* validate hashes and schema versions
* run simulation using evidence snapshots
* produce output and compare with stored artifact/simulation hash
* return:

  * `REPLAY_MATCHED` or `REPLAY_MISMATCHED`
  * diff summary (structured, not huge text)

### 7.2 Tolerances

Replays should match exactly if:

* deterministic ordering + quantization rules are enforced

If non-deterministic elements exist (timestamps), exclude them from hash and replay comparisons.

---

## 8. Missing Data Behavior (Standardized)

### 8.1 Missing price

* If `block_on_missing_prices=true`: BLOCKED + dq issue
* Else:

  * treat instrument as “unvalued” and mark PENDING_REVIEW (not recommended for institutional default)

### 8.2 Missing FX

Same as above; missing FX for funding is typically blocking.

### 8.3 Missing enrichment (issuer/liquidity)

* Does not block simulation by default
* But:

  * emits DQ issues
  * suitability section marks DATA_QUALITY issues
  * may trigger risk/compliance gate depending on policy pack

---

## 9. Implementation Plan

1. Introduce snapshot header models and enforce presence.
2. Implement canonical JSON serializer + Decimal normalization helper.
3. Implement request and snapshot hashing.
4. Implement DQ issue detection and DQ score calculation.
5. Wire DQ into proposal simulate response and artifact evidence bundle.
6. Implement replay endpoint (optional if persistence not ready; still valuable for tests).
7. Add tests + goldens focused on:

   * missing price
   * missing FX
   * stale market data
   * replay matched

---

## 10. Testing Plan

Unit tests:

* canonical hash stable for equivalent inputs
* DQ scoring deterministic
* staleness detection correct with fixed clock
* missing FX inversion logic covered

Golden tests:

* `scenario_14K_missing_price_blocked.json`
* `scenario_14K_stale_market_pending_review.json`
* `scenario_14K_replay_matched.json`

---

## 11. Acceptance Criteria (DoD)

* Responses include `data_quality` and `lineage` blocks.
* Request hash and snapshot hashes are computed deterministically.
* DQ issues are detected and scored deterministically.
* Staleness and missing data behaviors follow explicit options/policy.
* Replay endpoint can verify reproducibility against stored evidence.

---

## 12. Follow-ups

* Integration with an enterprise snapshot store (object storage)
* Data lineage persistence and governance hooks
* Expand DQ to cover corporate actions and reference-data mismatches

 




