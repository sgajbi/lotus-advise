# RFC-0014E: Advisory Proposal Artifact (Client-Ready Package + Evidence Bundle)

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-18 |
| **Target Release** | MVP-14E |
| **Depends On** | RFC-0014A (Proposal Simulation) |
| **Strongly Recommended** | RFC-0014B (Auto-Funding), RFC-0014C (Drift Analytics), RFC-0014D (Suitability Scanner) |
| **Doc Location** | `docs/rfcs/advisory pack/refine/RFC-0014E-proposal-artifact.md` |
| **Backward Compatibility** | Not required |
| **Implemented In** | 2026-02-19 |

---

## 0. Executive Summary

RFC-0014E introduces a **Proposal Artifact**: a deterministic, structured “package” that can be presented to:

- **Advisor UI** (proposal review & narrative)
- **Client communications** (what changes, why, impacts, risks)
- **Compliance/Risk reviewers** (evidence bundle, suitability deltas)
- **Downstream execution systems** (trade list, dependencies)

This RFC does not implement PDF/email generation. It defines and produces a **canonical JSON artifact** that can later be rendered into documents.

---

## 1. Motivation / Problem Statement

Your proposal engine already produces a simulation and an audit bundle, but advisory workflows require a **client-ready story**:

- “What are we proposing?”
- “Why now?”
- “How does it change my portfolio?”
- “What risks are introduced or mitigated?”
- “What assumptions were used (prices/FX snapshots)?”
- “What approvals are needed next (review, consent, execution)?”

The Proposal Artifact standardizes these elements in a deterministic structure.

---

## 2. Scope

### 2.1 In Scope
- Define a canonical `ProposalArtifact` schema.
- Add endpoint: `POST /rebalance/proposals/artifact` OR enhance `POST /rebalance/proposals/simulate` to optionally return `artifact`.
  - Recommended approach: keep simulate lean; expose a separate artifact endpoint that takes a simulation result (or the same request) and returns the artifact.
- Produce:
  - a proposal summary
  - trade & funding plan section
  - before/after allocations
  - drift improvement summary (if available)
  - suitability summary (if available)
  - assumptions & limitations
  - disclosures placeholders
  - evidence bundle for audit reproducibility

### 2.2 Out of Scope
- Persistence (saving proposals, versioning)
- Workflow state machine (consent/execution tracking)
- Document generation (PDF/Word/email)
- Fee/tax modeling (can be added later)

---

## 3. Design Principles

1) **Deterministic**: same input snapshot + same market snapshot + same options → same artifact  
2) **Explainable**: includes “why” as structured facts, not LLM free text  
3) **Composable**: UI/report layers can render each section independently  
4) **Auditable**: includes evidence bundle for reproducibility and reviewer confidence  
5) **No backward compatibility needed**: contract can be clean and strict

---

## 4. API Design

### 4.1 Option A (Implemented): Dedicated artifact endpoint
**Endpoint:** `POST /rebalance/proposals/artifact`

**Request options:**
- **A1:** Provide `proposal_simulate_request` (same as `/rebalance/proposals/simulate`) and internally call simulation first.
- **A2:** Provide `proposal_result` (the output of simulate) to avoid re-simulating.

For MVP, **A1 is implemented** (simpler for callers; artifact always matches simulation).

Headers:
- `Idempotency-Key` required
- `X-Correlation-Id` optional

Response:
- `200 OK` with `ProposalArtifact`

### 4.2 Option B: Embed artifact in simulate response
Add `options.include_artifact=true` to `/rebalance/proposals/simulate`.

This is acceptable, but tends to bloat the simulate response. Prefer Option A.

---

## 5. Proposal Artifact Schema

### 5.1 Top-level structure
```json
{
  "artifact_id": "pa_20260218_abcd1234",
  "proposal_run_id": "pr_...",
  "correlation_id": "corr_...",
  "created_at": "2026-02-18T09:12:00Z",
  "status": "READY|PENDING_REVIEW|BLOCKED",
  "gate_decision": { ... },

  "summary": { ... },
  "portfolio_impact": { ... },
  "trades_and_funding": { ... },
  "suitability_summary": { ... },
  "assumptions_and_limits": { ... },
  "disclosures": { ... },
  "evidence_bundle": { ... }
}
````

### 5.2 `summary`

```json
"summary": {
  "title": "Rebalance toward Balanced Model",
  "objective_tags": ["DRIFT_REDUCTION", "RISK_ALIGNMENT", "CASH_DEPLOYMENT"],
  "advisor_notes": [
    { "code": "NOTE", "text": "Client increased risk appetite slightly; deploying excess cash." }
  ],
  "recommended_next_step": "CLIENT_CONSENT|RISK_REVIEW|COMPLIANCE_REVIEW|NONE",
  "key_takeaways": [
    { "code": "DRIFT", "value": "Drift reduced from 12% to 7%" },
    { "code": "CASH", "value": "Cash reduced from 8% to 5%" }
  ]
}
```

Rules:

* `title` and `advisor_notes` are optional; deterministic defaults allowed.
* `key_takeaways` must be machine-derived facts (no generative text).

### 5.3 `portfolio_impact`

```json
"portfolio_impact": {
  "before": {
    "total_value": { "amount": "1200000.00", "currency": "SGD" },
    "allocation_by_asset_class": [ ... ],
    "allocation_by_instrument": [ ... ]
  },
  "after": {
    "total_value": { "amount": "1199999.98", "currency": "SGD" },
    "allocation_by_asset_class": [ ... ],
    "allocation_by_instrument": [ ... ]
  },
  "delta": {
    "total_value_delta": { "amount": "-0.02", "currency": "SGD" },
    "largest_weight_changes": [
      {
        "bucket_type": "INSTRUMENT",
        "bucket_id": "US_EQ_ETF",
        "weight_before": "0.12",
        "weight_after": "0.18",
        "delta": "0.06"
      }
    ]
  },
  "reconciliation": { ...same as simulation... }
}
```

### 5.4 `trades_and_funding`

```json
"trades_and_funding": {
  "trade_list": [
    {
      "intent_id": "oi_...",
      "type": "SECURITY_TRADE",
      "instrument_id": "US_EQ_ETF",
      "side": "BUY",
      "quantity": "10",
      "estimated_notional": { "amount": "1500.00", "currency": "USD" },
      "estimated_notional_base": { "amount": "2025.00", "currency": "SGD" },
      "dependencies": ["oi_fx_..."],
      "rationale": { "code": "DRIFT_REBALANCE", "message": "Reduce underweight to equities" }
    }
  ],
  "fx_list": [
    {
      "intent_id": "oi_fx_...",
      "pair": "USD/SGD",
      "buy_amount": "1500.00",
      "sell_amount_estimated": "2025.00",
      "rate": "1.3500"
    }
  ],
  "ordering_policy": "CASH_FLOW→SELL→FX→BUY",
  "execution_notes": [
    { "code": "DEPENDENCY", "text": "USD buys require FX conversion from SGD." }
  ]
}
```

Rules:

* Trade list must be in deterministic order.
* If RFC-0014B not implemented, `fx_list` may be empty and `dependencies` empty.

### 5.5 `suitability_summary` (if RFC-0014D present)

```json
"suitability_summary": {
  "new_issues": 2,
  "resolved_issues": 1,
  "persistent_issues": 3,
  "highest_severity_new": "HIGH",
  "highlights": [
    { "code": "NEW", "text": "Issuer concentration breach introduced for ISSUER_X" },
    { "code": "RESOLVED", "text": "Single position concentration reduced below 10%" }
  ],
  "issues": [ ... SuitabilityIssue ... ]
}
```

If scanner not present:

* omit this section or set `{ "status": "NOT_AVAILABLE" }`.

### 5.5B `gate_decision` (if RFC-0014F present)

When workflow gates are enabled, include deterministic workflow routing payload:
- `gate`
- `recommended_next_step`
- `reasons[]`
- `summary`

### 5.6 `assumptions_and_limits`

Must include explicit deterministic assumptions:

```json
"assumptions_and_limits": {
  "pricing": {
    "market_data_snapshot_id": "md_...",
    "prices_as_of": "2026-02-18T08:00:00Z",
    "fx_as_of": "2026-02-18T08:00:00Z",
    "valuation_mode": "CALCULATED"
  },
  "costs_and_fees": { "included": false, "notes": "Transaction costs, bid/ask spreads not modeled." },
  "tax": { "included": false, "notes": "Tax impact not modeled." },
  "execution": { "included": false, "notes": "Execution timing and slippage not modeled." }
}
```

### 5.7 `disclosures`

Placeholders (not jurisdiction-specific yet):

```json
"disclosures": {
  "risk_disclaimer": "This proposal is based on market data snapshots and does not guarantee future performance.",
  "product_docs": [
    { "instrument_id": "US_EQ_ETF", "doc_ref": "KID/FactSheet placeholder" }
  ]
}
```

### 5.8 `evidence_bundle`

This is the institutional core. It ensures reproducibility:

```json
"evidence_bundle": {
  "inputs": {
    "portfolio_snapshot": { ... },
    "market_data_snapshot": { ... },
    "shelf_entries": [ ... ],
    "options": { ... }
  },
  "engine_outputs": {
    "proposal_result": { ... full simulation output ... }
  },
  "hashes": {
    "request_hash": "sha256:....",
    "artifact_hash": "sha256:...."
  },
  "engine_version": "..."
}
```

Rules:

* `artifact_hash` is computed from canonical JSON serialization of the artifact payload excluding volatile fields.
* Ensure determinism: timestamps may break hash determinism; either:

  * exclude created_at from hash, or
  * use a deterministic created_at from request (not recommended)
    For MVP (implemented): **exclude volatile fields from hashing** (`created_at`, `artifact_hash`).

---

## 6. Generation Logic

### 6.1 Artifact generation pipeline

1. Run proposal simulation (RFC-0014A + optionally 14B/14C/14D)
2. Build `summary`:

   * recommended gate based on `status` + suitability (if available)
3. Build `portfolio_impact`:

   * reuse before/after allocations and compute deltas
4. Build `trades_and_funding`:

   * extract intents and convert to client-readable list
5. Add suitability summary (if present)
6. Add assumptions & limits from options + lineage
7. Attach evidence bundle (inputs + outputs)
8. Compute `artifact_hash` deterministically

### 6.2 Determinism requirements

* Stable ordering for:

  * allocations (sort by weight desc, then id)
  * trades (ordering policy)
  * suitability issues (existing deterministic sorting)
* Canonical JSON serialization for hashing.

---

## 7. Testing Plan

### 7.1 Unit tests

* Artifact determinism:

  * same request → identical artifact hash (excluding timestamp if excluded)
* Section correctness:

  * `portfolio_impact.delta` computed correctly
  * trade list grouping and ordering correct
* Evidence bundle includes required payloads and hashes

### 7.2 Golden tests

Add at least:

* `scenario_14E_artifact_basic.json` (proposal with manual trade + cash flow)
* `scenario_14E_artifact_with_fx.json` (if 14B present)
* `scenario_14E_artifact_with_suitability.json` (if 14D present)

Goldens should assert:

* presence and shape of all required sections
* stable ordering
* stable artifact_hash behavior per spec

---

## 8. Acceptance Criteria (DoD)

* Implemented: `/rebalance/proposals/artifact` returns a deterministic `ProposalArtifact`.
* Implemented: artifact includes summary, portfolio_impact (before/after/delta), trades_and_funding, assumptions, disclosures placeholders, evidence bundle.
* Implemented: if suitability is available, artifact includes suitability summary; otherwise section status is `NOT_AVAILABLE`.
* Implemented: evidence bundle includes full reproducibility payloads (inputs + engine outputs).
* Implemented: artifact hashing is deterministic and documented (canonical JSON excluding volatile fields).
* Implemented: golden tests cover multiple artifact scenarios end-to-end.

---

## 9. Follow-ups

* RFC-0014F: Workflow state machine + consent/execution lifecycle (with persistence later)
* RFC-0014G: Client document rendering (PDF/Word/email templates)
* RFC-0014H: Jurisdiction-specific disclosure packs and suitability mapping

 




