# RFC-0007A: Contract Tightening — Canonical Endpoint, Discriminated Intents, Valuation Policy, Universe Locking

**Status:** Draft
**Owner:** Lead Architect
**Created:** 2026-02-16
**Depends On:** RFC-0006A / RFC-0006B (Pre-persistence hardening)
**Backward Compatibility:** **Not required** (application not live)

---

## 0. Executive Summary

This RFC cleans up the public interface and core semantics to make the service unambiguous and institutional-grade:

1.  Establish one canonical endpoint and request/response schema (no duplicates).
2.  Replace "optional soup" intents with **discriminated union** intent types (SecurityTrade vs FxSpot).
3.  Make valuation behavior explicit via `valuation_mode` (CALCULATED vs TRUST_SNAPSHOT).
4.  Tighten universe/locking logic and handling of non-zero holdings deterministically.

This RFC intentionally breaks any old contract shape; we will update demos and tests accordingly.

---

## 1. Problem Statement

Pre-persistence, the most common institutional failures are ambiguity and drift:
* docs/demo and tests refer to different routes
* intent objects have many nullable fields, inviting incorrect consumers
* valuation behavior is an implicit choice
* holding overrides/locking apply only for `qty > 0`, which is not a robust invariant

---

## 2. Goals

### 2.1 Must-Have
* One canonical route and schema used everywhere.
* Strict intent schema:
    * `SecurityTradeIntent`: instrument_id required; quantity or notional required
    * `FxSpotIntent`: pair + amounts required
* Explicit valuation mode and documented behavior.
* Locking and universe eligibility computed consistently for all non-zero holdings.

### 2.2 Non-Goals
* Persistence / DB idempotency
* OMS execution integration

---

## 3. Canonical API (No Backward Compatibility)

### 3.1 Endpoint
**Canonical:** `POST /v1/rebalance/simulate`

Remove or rename any other similar routes (`/rebalance/simulate`, `/v1/rebalance`, etc.) so there is exactly one.

### 3.2 Required headers
* `Idempotency-Key` (required)
* `X-Correlation-Id` (optional)

### 3.3 Request schema (canonical)
Keep your existing schema, but ensure demos match this exactly:
```json
{
  "portfolio_id": "pf_123",
  "mandate_id": "mand_001",
  "portfolio_snapshot_id": "ps_...",
  "market_data_snapshot_id": "md_...",
  "options": {
    "valuation_mode": "CALCULATED",
    "allow_restricted": false,
    "suppress_dust_trades": true,
    "min_trade_notional_base": { "amount": 2000, "currency": "SGD" },
    "cash_band": { "min": 0.01, "max": 0.05 },
    "single_position_max_weight": 0.10,
    "block_on_missing_prices": true,
    "block_on_missing_fx": true
  }
}

```

---

## 4. Discriminated Intent Model (Contract-breaking Improvement)

### 4.1 Intent types

Replace single "OrderIntent" with a discriminated union:

#### 4.1.1 SecurityTradeIntent

```json
{
  "intent_type": "SECURITY_TRADE",
  "intent_id": "oi_...",
  "instrument_id": "ins_...",
  "side": "BUY|SELL",
  "quantity": 12.5,
  "notional": { "amount": 25000, "currency": "USD" },
  "notional_base": { "amount": 33500, "currency": "SGD" },
  "dependencies": ["oi_fx_..."],
  "rationale": { "code": "DRIFT_REBALANCE", "message": "..." },
  "constraints_applied": ["MIN_NOTIONAL", "ROUNDING"]
}

```

Rules:

* `instrument_id` required
* either `quantity` or `notional` must be present (prefer both when available)
* always include `notional_base` for auditability

#### 4.1.2 FxSpotIntent

```json
{
  "intent_type": "FX_SPOT",
  "intent_id": "oi_fx_...",
  "pair": "USD/SGD",
  "buy_currency": "USD",
  "buy_amount": 25000,
  "sell_currency": "SGD",
  "sell_amount_estimated": 33500,
  "dependencies": [],
  "rationale": { "code": "FUNDING", "message": "Fund USD buys" }
}

```

Rules:

* all FX fields required for FX intent
* no irrelevant fields allowed (no instrument_id, etc.)

### 4.2 Schema validation

* Fail fast at model validation for invalid intent combinations (request validation errors remain 4xx; domain errors remain 200 + BLOCKED per your chosen style).

---

## 5. Valuation Policy (Make it Explicit)

### 5.1 Options

Add required option:

* `options.valuation_mode`: `"CALCULATED"` or `"TRUST_SNAPSHOT"`

### 5.2 CALCULATED mode (default)

* All position values computed from `qty * price * fx` using the market snapshot
* If snapshot MV exists and differs beyond tolerance, add warning:
* `POSITION_VALUE_MISMATCH`


* Before-state and after-state are mathematically consistent with the same market snapshot.

### 5.3 TRUST_SNAPSHOT mode

* Before-state uses snapshot MV (base) if provided
* After-state uses computed valuation (still from the same market snapshot) unless you also supply an "execution MV" snapshot (not in scope here)
* If TRUST_SNAPSHOT causes reconciliation mismatch beyond tolerance:
* add warning `RECONCILIATION_MISMATCH_TRUST_SNAPSHOT`
* status becomes `PENDING_REVIEW` (recommended) rather than BLOCKED (policy choice; pick one)



---

## 6. Universe + Locking Semantics (Institutional)

### 6.1 Non-zero holdings

Locking/holding overrides must trigger for:

* `pos.quantity != 0` (not only `> 0`)

### 6.2 Negative holdings policy

If any `quantity < 0` is present in input snapshot:

* default: status BLOCKED + NO_SHORTING (HARD fail) + diagnostics listing instruments

(You can later add `options.allow_shorting=true`, but not required now.)

### 6.3 Shelf status behavior for held instruments

Define explicit behavior for holdings:

* SELL_ONLY held: sell allowed, buy blocked
* RESTRICTED held: sell allowed; buy allowed only if allow_restricted=true
* SUSPENDED held: freeze (no buy/sell); if engine attempts to trade it -> BLOCKED
* BANNED held: default forced liquidation unless `options.freeze_banned_holdings=true`

---

## 7. Implementation Plan

1. Choose canonical route `/v1/rebalance/simulate` and delete/rename other routes.
2. Update demo pack JSONs and tests to use the canonical route and schema.
3. Refactor intent models to discriminated union and update the engine and serializer.
4. Implement valuation_mode and add targeted unit tests for CALCULATED vs TRUST_SNAPSHOT.
5. Update universe/locking logic from `qty > 0` to `qty != 0`, and enforce negative holdings policy.

---

## 8. Acceptance Criteria (DoD)

* Exactly one simulate endpoint exists and is referenced everywhere.
* Intents are discriminated unions; no nullable junk fields.
* Valuation_mode is implemented and documented; behavior differences are test-covered.
* Locking applies to all non-zero holdings; negative holdings are handled deterministically.
* Demos and tests run cleanly with the new schema (no backward-compat shims).

