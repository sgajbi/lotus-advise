# RFC-0008: Advisory Proposal Funding and FX Dependency Policy

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-18 |
| **Depends On** | RFC-0006, RFC-0007 |
| **Doc Location** | `docs/rfcs/RFC-0008-advisory-proposal-auto-funding.md` |
| **Backward Compatibility** | Not required |
| **Implemented In** | 2026-02-19 |

---

## 0. Executive Summary

RFC-0008 upgrades advisory proposal evaluation to be more execution-realistic by adding
deterministic funding and FX dependency behavior:

- Automatically generate **FX spot intents** required to settle manual security trades.
- Build an explicit **dependency graph** (foreign-currency BUY depends on FX funding).
- Support **partial funding** (use existing foreign cash first; top up only the deficit).
- Enforce deterministic ordering: **CASH_FLOW → SELL → FX → BUY**.
- Provide clear diagnostics for missing FX, insufficient cash, and funding assumptions.

This enables advisors to evaluate realistic multi-currency proposals without manual FX math, while
keeping the outcome auditable and suitable for later workflow review.

Current architecture note:
- current funding logic is implemented inside `lotus-advise`,
- under `RFC-0006`, this RFC should be treated as the advisory funding-policy and dependency
  contract, not as a permanent claim that all underlying portfolio or execution logic belongs here.

---

## 1. Motivation / Problem Statement

RFC-0007 can evaluate advisor-proposed trades, but in private banking most buys are funded via:
- base-currency cash converted to the buy currency,
- proceeds from sells (possibly in multiple currencies),
- existing foreign cash pockets.

Without auto-funding:
- “BUY USD ETF” in a SGD base portfolio is not executable in reality.
- advisors must do manual FX math, weakening credibility of the simulation and proposal artifact.

---

## 2. Scope

### 2.1 In Scope
- Auto-generate FX spot intents to cover currency deficits created by proposed trades.
- Explicit dependencies from BUY intents to FX intents.
- Partial funding from existing cash and from sell proceeds (in their respective currencies).
- Deterministic intent ordering and deterministic FX intent grouping.
- Advisor- and reviewer-readable funding diagnostics and rationale.
- Funding-policy behavior that can later plug into jurisdiction, policy-pack, and execution flows.
- Diagnostics for:
  - missing FX rates
  - insufficient cash after considering all sources
  - ambiguous funding situations

### 2.2 Out of Scope
- Best execution / venue selection
- settlement lag / value dates / cutoffs
- transaction costs, spreads, slippage
- margin/overdraft/credit line funding (unless already present in your engine options)
- multi-leg FX strategies (triangulation beyond direct pair usage) unless explicitly implemented in market data
- Final execution-provider ownership, which belongs later in `RFC-0017`
- Jurisdiction-specific funding restrictions beyond explicit hooks and diagnostics

### 2.3 Architecture Alignment

This RFC should now be read under `RFC-0006`:

1. `lotus-advise` owns the advisory funding-plan contract and explainability surface,
2. canonical portfolio context and stateful sourcing belong with `lotus-core`,
3. `lotus-risk` may later validate funding-related risk outcomes or constraints,
4. `lotus-report` may later render funding explanation into review material,
5. `lotus-ai` may later explain funding choices, but does not replace deterministic funding logic.

---

## 3. Contract and Endpoint

### 3.1 Endpoint
Continues to use:
- `POST /advisory/proposals/simulate`

### 3.2 Inputs
No breaking changes required, but RFC-0008 introduces/standardizes these **options**:

```json
"options": {
  "auto_funding": true,
  "funding_mode": "AUTO_FX",
  "fx_funding_source_currency": "BASE_ONLY|ANY_CASH",
  "fx_generation_policy": "ONE_FX_PER_CCY",
  "block_on_missing_fx": true
}
````

Defaults:

* `auto_funding=true`
* `funding_mode=AUTO_FX`
* `fx_funding_source_currency=ANY_CASH` (use any available cash across currencies, then convert if needed)
* `fx_generation_policy=ONE_FX_PER_CCY`
* `block_on_missing_fx=true`

> Note: you can simplify by omitting some options initially, but the RFC defines them so behavior is explicit and testable.

Target-state note:
- as `RFC-0007` evolves toward explicit `stateless` and `stateful` operating modes, these funding
  options should remain part of the advisory evaluation contract rather than a service-local
  implementation detail.

---

## 4. Funding Model (Deterministic)

### 4.1 Definitions

* **Base currency**: portfolio base currency (e.g., SGD).
* **Trade currency**: instrument’s currency for security trades.
* **Available cash ledger**: cash balances by currency after applying:

  1. proposed cash flows
  2. proposed SELL trades (their proceeds)
  3. before-state cash balances

### 4.2 Funding priority rules

For each BUY in currency `CCY`:

1. Use available cash in `CCY` first.
2. If shortfall remains:

   * generate FX from a funding currency to `CCY`, then use proceeds.

Funding currency selection depends on `fx_funding_source_currency`:

* `BASE_ONLY`: always convert from base currency → `CCY`
* `ANY_CASH`: prefer base currency first; if base insufficient, then use other currencies with available cash in a deterministic order.

Deterministic funding-currency order for `ANY_CASH`:

1. base currency
2. other currencies sorted lexicographically by currency code (excluding target `CCY`)

> Implementation alignment note (current project slice):
> With `fx_generation_policy=ONE_FX_PER_CCY`, the engine selects a **single** funding currency
> per target currency using the deterministic order above. If no single source can fully fund
> the deficit, the proposal is blocked as insufficient funding.

For a gold-standard advisory product, the selected funding path should always be explainable to:

1. advisors preparing a recommendation,
2. reviewers validating operational realism,
3. downstream client-facing explanation layers where appropriate.

### 4.3 FX generation policy

`fx_generation_policy=ONE_FX_PER_CCY`:

* At most **one FX intent per target currency** per run.
* The FX intent amount equals the **net deficit** for that currency aggregated across all BUY intents (after considering existing cash and sells).

This makes the plan:

* predictable
* compact
* easy to audit
* easy for downstream execution engines

---

## 5. FX Spot Intent Specification

### 5.1 Model

FX intent uses a strict discriminated schema:

```json
{
  "intent_type": "FX_SPOT",
  "intent_id": "oi_fx_...",
  "pair": "USD/SGD",
  "buy_currency": "USD",
  "buy_amount": "25000.00",
  "sell_currency": "SGD",
  "sell_amount_estimated": "33750.00",
  "rate": "1.3500",
  "dependencies": [],
  "rationale": { "code": "FUNDING", "message": "Fund USD buys" }
}
```

### 5.2 Rate selection

* Use market snapshot FX rate for the exact `buy_currency/sell_currency` pair.
* If only inverse pair exists, invert deterministically:

  * rate(USD/SGD) = 1 / rate(SGD/USD)
* If neither exists:

  * if `block_on_missing_fx=true`: status BLOCKED + diagnostics.missing_fx
  * else: status PENDING_REVIEW with diagnostics warning and no FX intent generated

### 5.3 Notional estimation

* Security BUY notional in trade currency:

  * `notional_ccy = quantity * price_ccy`
* FX sell amount estimated:

  * `sell_amount = buy_amount * rate` (for pair buy/sell)
* All values are `Decimal` strings.
* Apply currency quantization rules via shared helper:

  * FX amounts typically 2 decimals (or currency-specific minor units)

---

## 6. Dependency Graph (Must)

### 6.1 BUY depends on FX

For every foreign-currency BUY where FX is generated:

* Add FX intent `intent_id` to BUY `dependencies[]`.

If no FX is needed (sufficient existing cash):

* `dependencies=[]`

### 6.2 Determinism

Dependency assignment must be deterministic:

* With one FX per currency, all BUYs in that currency depend on that FX intent.

---

## 7. Intent Ordering (Must)

Final intent list order must be:

1. CASH_FLOW intents (stable input order)
2. SECURITY_TRADE SELL intents (instrument_id asc)
3. FX_SPOT intents (pair asc)
4. SECURITY_TRADE BUY intents (instrument_id asc)

Within BUY intents, you may additionally sort by:

* trade currency, then instrument_id,
  to improve readability, but keep it deterministic.

---

## 8. Diagnostics & Rule Results

### 8.1 New diagnostics fields (recommended)

Add structured diagnostics sections:

```json
"diagnostics": {
  "missing_fx_pairs": ["USD/SGD"],
  "funding_plan": [
    {
      "target_currency": "USD",
      "required": "25000.00",
      "available_before_fx": "5000.00",
      "fx_needed": "20000.00",
      "fx_pair": "USD/SGD",
      "funding_currency": "SGD"
    }
  ],
  "insufficient_cash": [
    { "currency": "SGD", "deficit": "1500.00" }
  ]
}
```

### 8.2 Rule outcomes

* Missing FX (when blocking) is a **HARD** failure → `status=BLOCKED`.
* Insufficient cash after funding plan → **HARD** failure → `status=BLOCKED`.
* If missing FX is non-blocking, mark:

  * `status=PENDING_REVIEW`
  * and rule result `DATA_QUALITY` FAIL (or WARNING, depending on your rule taxonomy)

Current implementation marks missing non-blocking funding FX as `PENDING_REVIEW` and skips
execution-intent generation for affected BUYs in the simulated executable plan.

### 8.3 Gold-Standard Direction

Later revisions of this RFC should also support or prepare for:

1. policy-pack-aware funding restrictions,
2. jurisdiction-aware funding behavior hooks,
3. richer explanation of why a funding currency was chosen,
4. explicit separation between advisory funding-plan realism and execution-provider specifics.

---

## 9. Algorithm / Processing Pipeline

### 9.1 Steps (high-level)

1. Parse request, validate.
2. Build before-state.
3. Apply cash flows to cash ledger.
4. Apply SELL trades:

   * check oversell / no-short
   * add proceeds to cash ledger in instrument currency
5. Pre-compute BUY notionals in trade currency.
6. Build **funding plan**:

   * for each trade currency deficit, decide FX requirements
   * generate FX intents accordingly
7. Apply FX intents to cash ledger (estimated):

   * decrease sell_currency, increase buy_currency
8. Apply BUY trades:

   * decrease cash in trade currency
   * increase positions
9. Build after-state and reconciliation.
10. Run rule engine.
11. Emit response.

### 9.2 Important invariants

* Cash ledger never goes negative (unless an explicit overdraft option exists).
* All FX intents must be supported by market snapshot rates (or handled via policy).
* Output must be deterministic.
* Funding-path selection must be explainable and stable.

---

## 10. Examples

### 10.1 Example: partial funding

Before:

* USD cash = 5,000
* BUY USD ETF requires 25,000 USD
  Then:
* FX buy_amount = 20,000 USD
* BUY depends on FX intent
* BUY uses 5,000 existing USD + 20,000 from FX

### 10.2 Example response highlights

* `intents` includes:

  * FX_SPOT USD/SGD
  * BUY USD ETF with dependency on FX intent
* `diagnostics.funding_plan` documents the math

---

## 11. Testing Plan

### 11.1 Unit tests (core)

1. **No FX needed**:

   * existing foreign cash covers buy → no FX intent generated; dependencies empty
2. **FX needed**:

   * deficit exists → FX intent generated; BUY depends on FX
3. **Partial funding**:

   * some foreign cash exists → FX tops up remainder
4. **Missing FX (blocking)**:

   * no fx pair available → BLOCKED + diagnostics.missing_fx_pairs
5. **Insufficient base cash**:

   * even after sells, cannot fund FX sell amount → BLOCKED + diagnostics.insufficient_cash
6. **Determinism**:

   * same request twice → identical intent list and IDs (if you’ve implemented deterministic IDs)

### 11.2 Golden scenarios (new)

Add at least:

* `scenario_14B_auto_funding_single_ccy.json` (one FX currency)
* `scenario_14B_partial_funding.json`
* `scenario_14B_missing_fx_blocked.json`

Each golden must assert:

* order: CASH_FLOW → SELL → FX → BUY
* dependencies on BUY
* after-state cash and holdings reconcile

---

## 12. Acceptance Criteria (DoD)

* When `auto_funding=true`, the engine generates FX intents required to fund foreign BUYs.
* FX generation uses existing foreign cash first (partial funding supported).
* BUY intents include explicit dependencies on FX intents when FX is generated.
* Intent ordering is deterministic: CASH_FLOW → SELL → FX → BUY.
* Missing FX is handled per policy: blocking returns `status=BLOCKED` with clear diagnostics.
* Insufficient cash after considering all sources returns `status=BLOCKED`.
* Golden tests cover at least: FX needed, partial funding, missing FX.
* Funding diagnostics are clear enough for advisor and reviewer workflows.
* The RFC remains aligned with `RFC-0006` service boundaries and does not blur execution-provider
  or upstream data ownership.

---

## 13. Follow-ups (Next RFCs)

* RFC-0009: Drift analytics (before/after vs model alignment)
* RFC-0010: Suitability scanner (new/resolved/persistent issues)
* RFC-0011: Proposal artifact packaging (client-ready bundle + narrative)
* RFC-0012: Advisory workflow states + human-in-loop gates
* RFC-0017: execution integration interface

Related architecture RFCs:
- `RFC-0006`: target operating model and integration architecture
- `RFC-0007`: advisory proposal evaluation contract

---


## Behavior Reference (Implemented)

1. Auto-funding is option-controlled and runs only for BUY currency deficits.
2. Existing trade-currency cash is consumed before generating FX funding intents.
3. FX funding intents are generated deterministically and BUY intents carry explicit dependencies on those FX intents.
4. Missing required FX data follows policy: with blocking enabled the proposal is `BLOCKED`; with non-blocking policy execution intents are constrained and surfaced for review.
5. Intent ordering remains deterministic: `CASH_FLOW -> SELL -> FX -> BUY`.
6. This RFC defines the advisory funding and FX dependency policy; later execution ownership still
   belongs in `RFC-0017`.


