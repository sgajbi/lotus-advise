# RFC-0007: Advisory Proposal Evaluation Contract (Manual Trades + Cash Flows)

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-18 |
| **Depends On** | RFC-0004, RFC-0006 |
| **Doc Location** | `docs/rfcs/RFC-0007-advisory-proposal-simulate-mvp.md` |
| **Backward Compatibility** | Not required (new endpoint; app not live) |
| **Implemented In** | 2026-02-19 |

---

## 0. Executive Summary

This RFC defines the advisory proposal evaluation contract for the private-banking advisory workflow
where an advisor proposes **specific manual trades** and **cash flows** and needs to understand the
portfolio impact immediately.

This is **not** a full rebalance. It bypasses targeting and evaluates explicit advisor instructions
deterministically.

This RFC provides the proposal-evaluation foundation:
- `POST /advisory/proposals/simulate`
- Supports `proposed_trades[]` and `proposed_cash_flows[]`
- Applies cash flows **before** simulating trades
- Produces a full **before/after simulated state**, intents, and rule results (no-throw)

Current implementation note:
- the current implementation evaluates proposals inside `lotus-advise`,
- under `RFC-0006`, long-term canonical simulation authority should converge behind `lotus-core`,
- `lotus-advise` remains the advisory workflow and contract owner even when simulation authority is
  sourced upstream.

---

## 1. Motivation / Problem Statement

Advisors often need to pitch a **specific idea** ("sell X, buy Y, client deposits Z") rather than
trigger a full model-driven portfolio process.

Key gaps this RFC closes:
- **Operational gap:** simulate "what if" proposals without manual spreadsheet math.
- **Workflow gap:** create a proposal artifact that can later plug into suitability, consent, and execution steps.
- **Platform gap:** allow advisory proposals to reuse existing institutional infrastructure: deterministic simulation, after-state completeness, evidence bundle, rule results.

---

## 2. Scope

### 2.1 In Scope (RFC-0007)
1. **New endpoint**: `POST /advisory/proposals/simulate`
2. **Inputs**:
   - stateless advisory inputs
   - current implementation request payloads based on snapshots and proposal instructions
   - proposal trades (manual)
   - proposal cash flows (manual)
3. **Logic**:
   - bypass targeting
   - Apply cash flows **before** trade simulation.
   - Deterministic ordering of intents and deterministic output.
4. **Outputs**:
   - proposal result bundle including: before, after, intents, diagnostics, rule results,
     reconciliation, lineage IDs, and advisory-facing evaluation context

### 2.2 Explicitly Out of Scope (RFC-0007)
- **Auto-funding (FX generation)** (defer to RFC-0008)
- **Drift analytics (model alignment)** (defer to RFC-0009)
- **Suitability scanning / new vs resolved risks** (defer to RFC-0010)
- Persistence / DB / durable idempotency
- Final target-state upstream simulation sourcing from `lotus-core`

### 2.3 Architecture Alignment

This RFC should now be interpreted under `RFC-0006`:

1. `lotus-advise` owns the advisory-facing proposal evaluation contract,
2. `lotus-core` is the target authoritative source for stateful portfolio context and long-term
   canonical simulation authority,
3. `lotus-risk` owns risk analytics that may enrich or validate proposal outcomes in later slices,
4. `lotus-report` owns review/report payload generation,
5. `lotus-ai` may explain proposal outcomes, but does not replace deterministic evaluation.

---

## 3. Advisory Workflow Placement

This endpoint supports the "Idea -> Proposal" stage:

1. Advisor enters proposed trades + cash flows
2. Engine returns a deterministic simulation + audit bundle
3. Advisor reviews:
   - feasibility
   - safety hard blocks
   - after-state allocation
   - cash impact
4. Future RFCs will add:
   - suitability report for compliance narrative
   - proposal artifact packaging for client-facing documents
   - workflow gating to consent / execution

The endpoint should also support the `RFC-0004` workspace model, where proposal evaluation is part
of an iterative advisory drafting workflow rather than a one-off engine call.

---

## 4. Contract Decisions

### 4.1 Endpoint
`POST /advisory/proposals/simulate`

Rationale:
- Keep endpoint in the advisory `/advisory/...` family.
- Use explicit `proposals` resource naming for clarity.
- Keep clear separation between model-driven portfolio operations and manual advisory proposal
  evaluation.

### 4.2 Headers
- `Idempotency-Key` (required)
- `X-Correlation-Id` (optional; generated if missing)

### 4.3 Response codes
- `200 OK`: Always returned for domain outcomes (READY / PENDING_REVIEW / BLOCKED)
- `422 Unprocessable Entity`: schema validation errors
- `409 Conflict`: idempotency key mismatch (same key, different canonical request hash)
- `500`: unexpected bug (should not happen; must emit RFC7807)

**Important**: This RFC follows "no-throw domain outcomes" as described in the existing
architecture docs. Domain infeasibility should be surfaced in `status=BLOCKED` with rule results
and diagnostics rather than `422`.

---

## 5. Data Model

### 5.1 New Input Models

#### 5.1.1 ProposedCashFlow
```json
{
  "intent_type": "CASH_FLOW",
  "currency": "USD",
  "amount": "10000.00",
  "description": "Client deposit"
}
````

Rules:

* `amount > 0` -> deposit
* `amount < 0` -> withdrawal
* amount is `Decimal` string; no floats allowed

#### 5.1.2 ProposedTrade (manual)

Reuse the existing `SECURITY_TRADE` intent structure already used by the proposal-evaluation path,
but as an input.

```json
{
  "intent_type": "SECURITY_TRADE",
  "side": "BUY",
  "instrument_id": "AAPL",
  "quantity": "12"
}
```

Rules:

* Either `quantity` or `notional` must be provided (implementation may support both; must validate strictly)

### 5.2 ProposalSimulateRequest (canonical)

```json
{
  "portfolio_snapshot": { ... },
  "market_data_snapshot": { ... },
  "shelf_entries": [ ... ],
  "options": { ... },
  "proposed_cash_flows": [ ... ],
  "proposed_trades": [ ... ]
}
```

Notes:

* Current implementation keeps naming aligned with the existing snapshot-style request to reuse
  parsers, validators, and demo tooling.
* Target-state contract direction should converge on explicit `input_mode`, `stateless_input`,
  `stateful_input`, and `resolved_context` as described in `RFC-0006`.

### 5.3 ProposalResult (output)

`ProposalResult` should follow a stable simulation result shape to maximize reuse and maintain a consistent audit bundle across endpoints.

Minimum required fields:

* `proposal_run_id` (new prefix, e.g., `pr_...`)
* `correlation_id`
* `status` (READY / PENDING_REVIEW / BLOCKED)
* `before` (full)
* `intents` (includes cash flows + trades, deterministic ordering)
* `after_simulated` (full)
* `rule_results`
* `diagnostics`
* `lineage`:

  * `request_hash`
  * snapshot IDs if provided
  * engine version
* `resolved_context` (target-state requirement for stateful sourcing and replay clarity)

---

## 6. Algorithm / Processing Pipeline

### 6.1 Deterministic intent ordering

To avoid ambiguity and support deterministic goldens, intent ordering must be:

1. `CASH_FLOW` intents (as provided, stable order)
2. `SECURITY_TRADE` SELL intents (instrument_id ascending)
3. `SECURITY_TRADE` BUY intents (instrument_id ascending)

> Auto-generated FX intents are not part of RFC-0007 (added in RFC-0008).

### 6.2 Core flow

1. **Validate request**

   * schema validation
   * enforce Decimal strings
   * enforce required headers

2. **Build before-state**

   * compute portfolio total value in base currency
   * compute allocations (by instrument + by asset class if available)
   * compute reconciliation baseline

3. **Apply cash flows**

   * adjust cash balances by currency
   * enforce:

     * withdrawals cannot make cash negative unless an explicit overdraft facility exists (not in scope here -> default: block)
   * record diagnostics for any issues

4. **Simulate manual trades**

   * use existing simulator primitives (same as rebalance after-state simulation)
   * enforce safety:

     * no-short / no-oversell
     * shelf semantics: do not allow BUY for SELL_ONLY / BANNED / SUSPENDED
     * missing price/fx handling based on existing options flags

5. **Run rule engine**

   * same rule set as rebalance (as already implemented)
   * produce rule results and set status:

     * any HARD fail -> BLOCKED
     * soft fails -> PENDING_REVIEW
     * else READY

6. **Return ProposalResult**

   * include complete `after_simulated`
   * include reconciliation proof

---

## 7. Diagnostics and Reason Codes

RFC-0007 adds these proposal-specific diagnostics codes:

* `PROPOSAL_WITHDRAWAL_NEGATIVE_CASH` (hard block)
* `PROPOSAL_INVALID_TRADE_INPUT` (schema-level 422)
* `PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF` (hard block if BUY of disallowed instrument)

Reuses existing shared safety reason codes:

* `NO_SHORTING`
* `SELL_EXCEEDS_HOLDINGS`
* `INSUFFICIENT_CASH`
* missing price/fx reason codes (based on existing implementation)

Advisory-facing outputs should remain product-readable and suitable for later explanation layers in
`lotus-ai`, not just engine-readable.

---

## 8. Examples

### 8.1 Example request

```json
{
  "portfolio_snapshot": {
    "portfolio_id": "pf_advisory_01",
    "base_currency": "SGD",
    "positions": [
      { "instrument_id": "SG_BOND_ETF", "quantity": "100", "currency": "SGD" }
    ],
    "cash_balances": [
      { "currency": "SGD", "amount": "5000.00" },
      { "currency": "USD", "amount": "0.00" }
    ]
  },
  "market_data_snapshot": {
    "prices": [
      { "instrument_id": "SG_BOND_ETF", "price": "100.00", "currency": "SGD" },
      { "instrument_id": "US_EQ_ETF", "price": "150.00", "currency": "USD" }
    ],
    "fx_rates": [
      { "pair": "USD/SGD", "rate": "1.35" }
    ]
  },
  "shelf_entries": [
    { "instrument_id": "SG_BOND_ETF", "status": "APPROVED", "asset_class": "BOND" },
    { "instrument_id": "US_EQ_ETF", "status": "APPROVED", "asset_class": "EQUITY" }
  ],
  "options": {
    "block_on_missing_prices": true,
    "block_on_missing_fx": true,
    "suppress_dust_trades": true
  },
  "proposed_cash_flows": [
    { "intent_type": "CASH_FLOW", "currency": "SGD", "amount": "10000.00", "description": "Client top-up" }
  ],
  "proposed_trades": [
    { "intent_type": "SECURITY_TRADE", "side": "BUY", "instrument_id": "US_EQ_ETF", "quantity": "10" }
  ]
}
```

### 8.2 Example response (shape)

```json
{
  "proposal_run_id": "pr_20260218_abcd1234",
  "correlation_id": "corr_...",
  "status": "PENDING_REVIEW",
  "before": { "... full state ..." },
  "intents": [
    { "intent_type": "CASH_FLOW", "currency": "SGD", "amount": "10000.00", "description": "Client top-up" },
    { "intent_type": "SECURITY_TRADE", "side": "BUY", "instrument_id": "US_EQ_ETF", "quantity": "10", "dependencies": [] }
  ],
  "after_simulated": { "... full state ..." },
  "rule_results": [ "... existing rules ..." ],
  "diagnostics": [ "... any issues ..." ],
  "lineage": {
    "idempotency_key": "....",
    "request_hash": "sha256:....",
    "engine_version": "..."
  }
}
```

---

## 9. Testing Plan

### 9.1 Unit tests (new)

1. Cash flow application:

   * deposit increases cash correctly
   * withdrawal that makes cash negative -> BLOCKED + diagnostic
2. Manual trade simulation:

   * BUY reduces cash
   * SELL increases cash
   * oversell blocks
3. Determinism:

   * stable intent ordering
   * identical request yields identical output JSON (golden friendly)

### 9.2 Golden scenario (new)

Add: `tests/unit/advisory/golden_data/scenario_14A_advisory_manual_trade_cashflow.json`

Scenario:

* Portfolio: base SGD, has SGD cash + a holding
* Proposal:

  * deposit SGD 10,000
  * BUY an approved instrument with known price
    Expected:
* `after_simulated` includes updated cash and position
* status READY/PENDING_REVIEW depending on configured cash band / min trade settings
* reconciliation passes

### 9.3 Gold-Standard Direction

Later revisions of this RFC should also validate:

1. stateful proposal sourcing via `lotus-core`,
2. stable `resolved_context` emission for replay and supportability,
3. normalized evaluation output quality for `lotus-workbench` and `lotus-gateway`,
4. compatibility with `lotus-risk` enrichment and `RFC-0004` workspace reevaluation flows.

---

## 10. Rollout

1. Add endpoint behind docs/demo usage (no persistence)
2. Validate with a small scenario set (goldens)
3. Extend with RFC-0008 (Auto-Funding) once RFC-0007 stabilizes
4. Converge later revisions toward the `RFC-0006` stateful/stateless contract model

---

## 11. Follow-up RFCs (Planned)

* **RFC-0008**: Auto-Funding for Proposals (FX spot intent generation + dependencies)
* **RFC-0009**: Drift Analytics (Before/After vs Model alignment metrics)
* **RFC-0010**: Suitability Scanner v1 (New/Resolved/Persistent issues)
* **RFC-0011**: Proposal Artifact Packaging (client-ready narrative bundle)

Related architecture RFCs:
- `RFC-0004`: iterative advisory workspace contract
- `RFC-0006`: target operating model and integration architecture

---


## Behavior Reference (Implemented)

1. Inputs are simulated in deterministic sequence: cash flows first, then security trades with stable ordering.
2. Proposal BUYs on disallowed shelf statuses are hard-blocked with proposal-specific diagnostics.
3. If `proposal_block_negative_cash=true`, withdrawal-driven negative cash is hard-blocked.
4. Final status is still derived from shared hard/soft rule semantics (`READY`, `PENDING_REVIEW`, `BLOCKED`).
5. Idempotency behavior is deterministic: same `Idempotency-Key` plus same canonical payload returns cached-equivalent output; same key with different payload returns conflict.
6. This RFC defines the advisory proposal evaluation surface; target-state upstream simulation
   authority should align to `lotus-core` under `RFC-0006`.


