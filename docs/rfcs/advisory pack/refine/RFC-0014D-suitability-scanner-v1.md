# RFC-0014D: Suitability Scanner v1 for Advisory Proposals (New / Resolved / Persistent Issues)

| Metadata | Details |
| --- | --- |
| **Status** | IMPLEMENTED |
| **Created** | 2026-02-18 |
| **Target Release** | MVP-14D |
| **Depends On** | RFC-0014A (Proposal Simulation), RFC-0006A (After-state completeness & safety) |
| **Optional Depends On** | RFC-0014B (Auto-funding), RFC-0014C (Drift analytics) |
| **Doc Location** | `docs/rfcs/advisory pack/refine/RFC-0014D-suitability-scanner-v1.md` |
| **Backward Compatibility** | Not required |
| **Implemented In** | 2026-02-19 |

---

## 0. Executive Summary

RFC-0014D adds a **Suitability Scanner v1** to the advisory proposal workflow. It evaluates the portfolio **before** and **after** simulation and produces a structured list of suitability issues, categorized as:

- **NEW** (introduced by the proposal)
- **RESOLVED** (fixed by the proposal)
- **PERSISTENT** (still present after the proposal)

This is not a full pre-trade compliance engine. It is an **advisory-grade suitability summary** designed to:
- support advisor narrative (“what risks did we fix / introduce?”)
- support review gates (“needs compliance review?”)
- provide an auditable evidence bundle (deterministic outputs)

---

## 1. Motivation / Problem Statement

In private banking advisory, an “investment proposal” must be paired with:
- a suitability narrative,
- evidence that the proposal improves or at least does not worsen key constraints,
- explicit disclosure of any new risks introduced.

Your rough RFC idea references a “5-point scan” concept and highlights that suitability should compare current vs proposed state.
RFC-0014D formalizes that scanner in a deterministic, testable way.

---

## 2. Scope

### 2.1 In Scope
- Add `suitability` section to proposal simulation response.
- Implement Suitability Scanner v1 checks (configurable thresholds):
  1) **Single position concentration**
  2) **Issuer concentration** (requires issuer id)
  3) **Liquidity bucket exposure**
  4) **Product governance / shelf restrictions** (sell-only, suspended, banned)
  5) **Cash band** (advisory view; separate from hard rule engine)

- Provide **NEW/RESOLVED/PERSISTENT** classification by comparing before vs after.

### 2.2 Out of Scope
- Full regulatory suitability framework per jurisdiction (MiFID/MAS/FINMA)
- Product-specific suitability (structured notes payoff risk, FX options, etc.)
- Client-specific suitability (risk tolerance questionnaire mapping, time horizon, knowledge/experience)
- Tax/regulatory reporting
- Portfolio risk model (VaR, stress) — separate RFC

---

## 3. Key Design Decision: Suitability Scanner vs Rule Engine

The project already has a “rule_results” concept used to determine READY/PENDING_REVIEW/BLOCKED. Suitability Scanner v1 is **separate**:

- **Rule Engine**: deterministic “can we proceed?” checks; may block.
- **Suitability Scanner**: advisory summary & narrative; does not block by itself, but can recommend review gates.

**Output must include both**:
- `rule_results`: existing style for execution readiness
- `suitability`: advisory suitability matrix (new/resolved/persistent)

---

## 4. Data Requirements

To compute suitability, we require the following data enrichment:

### 4.1 From Shelf Entries
Each `shelf_entry` must include (or be derivable):
- `instrument_id`
- `status`: APPROVED / RESTRICTED / SELL_ONLY / SUSPENDED / BANNED
- `asset_class`
- `issuer_id` (required for issuer concentration)
- `liquidity_tier` (required for liquidity exposure)
  - e.g., `L1` (highly liquid) … `L5` (illiquid)
- Optional: `product_type`, `risk_rating` (not required in v1)

If any required enrichment is missing:
- scanner should emit a `DATA_QUALITY` suitability issue (severity configurable)
- and rely on existing rule engine options for blocking vs warning

### 4.2 From State
Scanner uses portfolio weights (in base currency) from:
- `before.allocation_by_instrument`
- `after_simulated.allocation_by_instrument`

If those allocations are missing, this RFC requires BLOCKED (this is already part of institutional after-state completeness).

---

## 5. Suitability Issue Model

### 5.1 SuitabilityIssue
```json
{
  "issue_id": "SUIT_SINGLE_POSITION_MAX",
  "dimension": "CONCENTRATION|ISSUER|LIQUIDITY|GOVERNANCE|CASH|DATA_QUALITY",
  "severity": "LOW|MEDIUM|HIGH",
  "status_change": "NEW|RESOLVED|PERSISTENT",
  "summary": "Single position exceeds 10% cap",
  "details": {
    "threshold": "0.10",
    "measured_before": "0.12",
    "measured_after": "0.09",
    "instrument_id": "US_EQ_ETF"
  },
  "evidence": {
    "as_of": "2026-02-18",
    "snapshot_ids": {
      "portfolio_snapshot_id": "...",
      "market_data_snapshot_id": "..."
    }
  }
}
````

### 5.2 Identity / Deduplication rule

To classify before vs after, issues must have stable keys.
Define a deterministic `issue_key` that includes dimension and entity:

* Single position: `SINGLE_POSITION_MAX|<instrument_id>`
* Issuer: `ISSUER_MAX|<issuer_id>`
* Liquidity: `LIQUIDITY_MAX|<liquidity_tier>`
* Governance: `GOVERNANCE|<instrument_id>|<shelf_status>`
* Cash: `CASH_BAND`
* Data quality: `DQ|<type>|<entity>`

Classification:

* Present in after but not before => NEW
* Present in before but not after => RESOLVED
* Present in both => PERSISTENT

---

## 6. Scanner Checks (v1)

> Thresholds come from `options.suitability_thresholds` with defaults.

### 6.1 Single Position Concentration

Compute instrument weights. For each instrument:

* if weight > `single_position_max_weight` => issue

Defaults:

* `single_position_max_weight = 0.10`

Severity heuristic:

* HIGH if > cap * 1.25
* MEDIUM if > cap
* LOW if within cap but close to cap (optional “watchlist”)

### 6.2 Issuer Concentration

Group by `issuer_id` from shelf entries. Sum weights.

* if issuer_weight > `issuer_max_weight` => issue

Defaults:

* `issuer_max_weight = 0.20`

### 6.3 Liquidity Exposure

Group instruments by `liquidity_tier`. Sum weights.
Rules are typically: “illiquid exposure must not exceed X%”.

Defaults example:

* `max_weight_by_liquidity_tier`:

  * `L4`: 0.10
  * `L5`: 0.05

### 6.4 Product Governance / Shelf Restrictions

Use shelf status for each instrument:

* If instrument is **BANNED** and is present in portfolio => issue HIGH
* If **SUSPENDED** and present => issue HIGH
* If **SELL_ONLY** and portfolio weight increases in after-state => issue HIGH (proposal violates sell-only)
* If **RESTRICTED** and increases and `allow_restricted=false` => issue HIGH (proposal violates restriction)
* If **RESTRICTED** and increases and allow is true => issue MEDIUM with disclosure (“restricted allowed”)

Implementation alignment note:
- Advisory execution guards can block disallowed BUYs before they change after-state holdings.
- Suitability scanner therefore also emits governance issues for attempted BUYs in `SELL_ONLY` and `RESTRICTED` instruments so NEW violations remain visible in blocked proposals.

### 6.5 Cash Band (Suitability View)

Compute cash weight after proposal.

* If cash weight outside [min,max] => suitability issue MEDIUM (unless rule engine already treats as HARD/soft)

Defaults:

* min=0.01, max=0.05

This is advisory; it helps narrative like “proposal uses too much cash”.

### 6.6 Data Quality Suitability Issues

If scanner cannot compute a check due to missing enrichment:

* issue_id: `SUIT_DATA_QUALITY`
* severity: MEDIUM (default)
* dimension: DATA_QUALITY
* details: missing fields list

Whether this blocks is governed by existing options and rule engine.

---

## 7. Output Structure

### 7.1 Add to ProposalResult

```json
"suitability": {
  "summary": {
    "new_count": 2,
    "resolved_count": 1,
    "persistent_count": 3,
    "highest_severity_new": "HIGH"
  },
  "issues": [
    { "... SuitabilityIssue ..." }
  ]
}
```

### 7.2 Sorting rules (deterministic)

Sort issues by:

1. status_change order: NEW, PERSISTENT, RESOLVED
2. severity: HIGH, MEDIUM, LOW
3. dimension
4. issue_key lexicographically

---

## 8. Workflow Gate Recommendation (non-blocking hint)

Add optional field:

```json
"suitability": {
  "recommended_gate": "NONE|RISK_REVIEW|COMPLIANCE_REVIEW"
}
```

Default logic:

* if any NEW HIGH issue => `COMPLIANCE_REVIEW`
* else if any NEW MEDIUM issue => `RISK_REVIEW`
* else `NONE`

This does not change status; status remains driven by rule engine unless you decide otherwise in a later RFC.

---

## 9. Implementation Plan

1. Add `SuitabilityThresholds` to options:

   * single_position_max_weight
   * issuer_max_weight
   * liquidity caps map
   * cash band
2. Add `SuitabilityScanner` module:

   * `scan(before_state, after_state, shelf_entries, options) -> SuitabilityResult`
3. Implement check calculators:

   * weights extraction
   * issuer grouping
   * liquidity grouping
   * governance status checks
4. Implement before/after classification:

   * compute issue_map_before, issue_map_after keyed by issue_key
   * create NEW/RESOLVED/PERSISTENT list
5. Wire result into proposal response builder
6. Add unit tests and goldens

---

## 10. Testing Plan

### 10.1 Unit tests

* Single position breach detected and classified correctly
* Issuer breach detected with correct issuer aggregation
* Liquidity tier breach detected
* Governance:

  * SELL_ONLY increase => HIGH NEW
  * BANNED holding => HIGH PERSISTENT/NEW depending on before
* Classification:

  * issue appears only after => NEW
  * only before => RESOLVED
  * both => PERSISTENT
* Sorting deterministic

### 10.2 Golden scenarios (new)

Add:

* `scenario_14D_single_position_resolved.json`

  * before breaches cap, after fixes => RESOLVED
* `scenario_14D_new_issuer_breach.json`

  * proposal introduces issuer breach => NEW
* `scenario_14D_sell_only_violation.json`

  * proposal increases sell-only => NEW HIGH + recommended_gate=COMPLIANCE_REVIEW

Each golden asserts:

* suitability.summary counts
* issue list ordering
* recommended_gate value

---

## 11. Acceptance Criteria (DoD)

* Proposal response includes `suitability` when enabled (default enabled).
* Suitability issues computed deterministically for before and after.
* Issues are classified into NEW/RESOLVED/PERSISTENT correctly.
* Governance restrictions are correctly recognized and produce HIGH issues when violated.
* Golden tests cover at least 3 scenarios with stable outputs.

---

## 12. Follow-ups

* RFC-0014E: Proposal Artifact Packaging (client-ready narrative sections)
* RFC-0014F: Workflow gating as first-class state machine (with persistence later)


## Behavior Reference (Implemented)

1. Suitability scanner is deterministic and classifies issues as `NEW`, `PERSISTENT`, or `RESOLVED` by comparing before vs after states.
2. Scanner output is advisory-focused and complements, rather than replaces, hard/soft rule-engine status decisions.
3. Governance-related attempted violations are still surfaced as suitability issues even when execution guards block the trade.
4. `recommended_gate` is derived from new-issue severity and consumed by shared workflow-gate policy.
