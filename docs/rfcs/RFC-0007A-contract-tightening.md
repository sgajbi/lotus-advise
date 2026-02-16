# RFC-0007A: Contract Tightening — Canonical Endpoint, Discriminated Intents, Valuation Policy, Universe Locking

**Status:** Draft
**Owner:** Lead Architect
**Created:** 2026-02-16
**Depends On:** RFC-0006A / RFC-0006B (Pre-persistence hardening)
**Backward Compatibility:** **Not required** (application not live)

**Doc Location:** `docs/rfcs/RFC-0007A-contract-tightening.md`

---

## 0. Executive Summary

This RFC cleans up the public interface and core semantics to make the service unambiguous and institutional-grade:

1.  **Canonical Endpoint:** Establish one canonical endpoint (`POST /v1/rebalance/simulate`) and request/response schema.
2.  **Discriminated Intents:** Replace “optional soup” intents with **discriminated union** intent types (`SecurityTrade` vs `FxSpot`).
3.  **Explicit Valuation:** Make valuation behavior explicit via `valuation_mode` (`CALCULATED` vs `TRUST_SNAPSHOT`).
4.  **Universe Locking:** Tighten universe/locking logic to handle all non-zero holdings deterministically.

This RFC intentionally breaks any old contract shape; we will update demos and tests accordingly.

---

## 1. Problem Statement

Pre-persistence, the most common institutional failures are ambiguity and drift:
* **Route Confusion:** docs/demo and tests refer to different routes.
* **Intent Ambiguity:** Intent objects have many nullable fields, inviting incorrect consumers to guess structure.
* **Implicit Valuation:** The engine currently makes implicit choices about whether to trust the input `market_value` or recalculate it from `price * qty`.
* **Holding Invariants:** Holding overrides/locking apply only for `qty > 0`, which ignores short positions or dust, failing robust invariant checks.

---

## 2. Goals

### 2.1 Must-Have
* **One Canonical Route:** `/v1/rebalance/simulate` used everywhere.
* **Strict Intent Schema:**
    * `SecurityTradeIntent`: `instrument_id` required; `quantity` or `notional` required.
    * `FxSpotIntent`: `pair` + amounts required; no `instrument_id`.
* **Explicit Valuation Mode:** `options.valuation_mode` must be set or default explicitly.
* **Robust Locking:** Universe eligibility computed consistently for *all* non-zero holdings (including negative).

### 2.2 Non-Goals
* Persistence / DB idempotency (deferred to RFC-0008).
* OMS execution integration (downstream).

---

## 3. Canonical API (No Backward Compatibility)

### 3.1 Endpoint
**Canonical:** `POST /v1/rebalance/simulate`

*Action:* Remove or rename any other similar routes (`/rebalance/simulate`, `/v1/rebalance`, etc.) so there is exactly one.

### 3.2 Required Headers
* `Idempotency-Key` (Required): SHA-256 of canonical inputs or UUID.
* `X-Correlation-Id` (Optional): Trace ID for logging.

### 3.3 Request Schema (Canonical)
Keep existing schema, but ensure demos match this exactly. Add `options.valuation_mode`.

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

### 4.1 Intent Types

Replace single `OrderIntent` with a discriminated union.

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

**Rules:**

* `instrument_id` required.
* Either `quantity` or `notional` must be present.
* Always include `notional_base` for auditability.

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

**Rules:**

* All FX fields required.
* No irrelevant fields allowed (no `instrument_id`).

### 4.2 Schema Validation

* Fail fast at Pydantic model validation for invalid intent combinations.

---

## 5. Valuation Policy (Make it Explicit)

### 5.1 Options

Add required option: `options.valuation_mode`: `"CALCULATED"` (Default) or `"TRUST_SNAPSHOT"`.

### 5.2 CALCULATED Mode (Default)

* All position values computed from `qty * price * fx` using the market snapshot.
* If snapshot MV exists and differs from calculated > tolerance, add warning `POSITION_VALUE_MISMATCH`.
* **Benefit:** Before-state and after-state are mathematically consistent with the same market snapshot.

### 5.3 TRUST_SNAPSHOT Mode

* Before-state uses snapshot MV (base) if provided.
* After-state uses computed valuation (unless "execution MV" snapshot provided).
* If `TRUST_SNAPSHOT` causes reconciliation mismatch > tolerance:
* Add warning `RECONCILIATION_MISMATCH_TRUST_SNAPSHOT`.
* Status becomes `PENDING_REVIEW`.



---

## 6. Universe + Locking Semantics (Institutional)

### 6.1 Non-zero Holdings

Locking/holding overrides must trigger for `pos.quantity != 0` (not just `> 0`).

### 6.2 Negative Holdings Policy

If any `quantity < 0` is present in input snapshot:

* Default: Status `BLOCKED` + `NO_SHORTING` (HARD fail) + diagnostics listing instruments.
* (Future: `options.allow_shorting=true`).

### 6.3 Shelf Status Behavior for Held Instruments

* **SELL_ONLY held:** Sell allowed, Buy blocked.
* **RESTRICTED held:** Sell allowed; Buy allowed only if `allow_restricted=true`.
* **SUSPENDED held:** Freeze (no buy/sell). If engine logic attempts to trade it -> `BLOCKED`.
* **BANNED held:** Default forced liquidation unless `options.freeze_banned_holdings=true`.

---

## 7. Implementation Plan

1. **Refactor API:** Implement `POST /v1/rebalance/simulate` and delete old routes.
2. **Update Demo Pack:** Fix all JSONs and tests to match new schema.
3. **Refactor Models:** Split `OrderIntent` into `SecurityTradeIntent` and `FxSpotIntent`.
4. **Implement Valuation Logic:** Add `ValuationService` branch for `CALCULATED` vs `TRUST_SNAPSHOT`.
5. **Harden Universe:** Update locking logic to `qty != 0`.

---

## 8. Acceptance Criteria (DoD)

1. Exactly one simulate endpoint exists.
2. Intents are discriminated unions in the response.
3. `options.valuation_mode` changes behavior as documented.
4. Locking applies to all non-zero holdings.
5. `ruff check` and `pytest` pass 100%.

```

```