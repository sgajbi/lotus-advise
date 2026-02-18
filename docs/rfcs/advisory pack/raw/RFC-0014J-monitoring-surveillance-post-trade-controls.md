# RFC-0014J: Monitoring, Surveillance & Post-Trade Controls (Institution-Grade Oversight)

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
| **Created** | 2026-02-18 |
| **Target Release** | MVP-14J |
| **Depends On** | RFC-0014I (Execution Integration) |
| **Strongly Recommended** | RFC-0014G (Persistence), RFC-0014H (Policy Packs) |
| **Doc Location** | `docs/rfcs/RFC-0014J-monitoring-surveillance-post-trade-controls.md` |
| **Backward Compatibility** | Not required |

---

## 0. Executive Summary

RFC-0014J adds **institution-grade oversight** after proposals enter execution:

- **Post-trade reconciliation**: compare expected vs executed positions/cash
- **Surveillance signals**: unusual trading patterns, concentration spikes, liquidity breaches
- **Breach monitoring**: detect when post-trade state violates policy packs
- **Exception workflows**: structured exceptions with reason codes and remediation suggestions
- **Operational monitoring**: health, latency, error budgets, and audit completeness

This RFC ensures the system is not just “able to trade”, but “able to be trusted”.

---

## 1. Motivation / Problem Statement

In production private banking, the biggest risks are often not “making a proposal,” but:

- execution differs from proposal (partial fills, slippage, rejected legs)
- portfolio ends up breaching internal or jurisdiction constraints
- data gaps cause silent drift or misreporting
- operational issues (timeouts, retries) cause duplicate orders or missing audit trails

RFC-0014J closes the loop with monitoring + controls.

---

## 2. Scope

### 2.1 In Scope
- Post-trade reconciliation engine (proposal expected vs executed)
- Policy-based post-trade checks (using Policy Packs)
- Surveillance signals generation
- Exception objects and remediation recommendations
- Observability metrics and logs for oversight

### 2.2 Out of Scope
- Full market surveillance (cross-client insider trading detection etc.)
- Trade cost analysis (TCA) deep analytics (later RFC)
- Regulatory reporting submissions (separate workstream)

---

## 3. Core Concepts

### 3.1 Expected State vs Realized State
- **Expected**: derived from ProposalArtifact and execution tickets
- **Realized**: derived from execution fill events and/or updated portfolio snapshots

### 3.2 Exception
A structured record describing a deviation or breach requiring attention.

---

## 4. Data Requirements

Inputs:
- proposal version artifact + evidence bundle (immutable)
- execution tickets + fill events
- latest portfolio snapshot after execution (preferred) OR reconstructed ledger from fills
- policy pack for jurisdiction/mandate

---

## 5. Post-Trade Reconciliation

### 5.1 Reconciliation dimensions
1) **Positions**
   - expected quantity change vs executed filled quantity
2) **Cash**
   - expected cash impact vs realized cash impact per currency
3) **FX**
   - expected FX buy/sell amounts vs executed
4) **Notional & pricing**
   - expected notionals vs realized (using fill prices)
5) **Dependencies**
   - detect broken dependency chains (e.g., buy executed before FX)

### 5.2 Reconciliation output schema
```json
"post_trade_reconciliation": {
  "execution_id": "exec_...",
  "status": "MATCHED|PARTIAL|MISMATCHED|UNKNOWN",
  "position_deltas": [
    {
      "instrument_id": "US_EQ_ETF",
      "expected_qty_change": "10",
      "filled_qty": "7",
      "remaining_qty": "3",
      "status": "PARTIAL"
    }
  ],
  "cash_deltas": [
    {
      "currency": "USD",
      "expected_change": "-1500.00",
      "realized_change": "-1100.00",
      "status": "PARTIAL"
    }
  ],
  "notes": [ ... ]
}
````

Classification rules:

* `MATCHED` if all instruments/cash within tolerance
* `PARTIAL` if partial fills exist but consistent
* `MISMATCHED` if unexpected fills, overfills, or cash breaks tolerance
* `UNKNOWN` if insufficient data (e.g., missing portfolio snapshot)

---

## 6. Post-Trade Policy Checks (Breach Detection)

Re-run selected checks against the realized post-trade state (using RFC-0014H policy packs):

* Single position concentration
* Issuer concentration
* Liquidity exposure caps
* Governance status violations (banned/suspended holdings)
* Cash band

Output:

```json
"post_trade_breaches": [
  {
    "breach_id": "BREACH_ISSUER_MAX|ISSUER_X",
    "severity": "HIGH",
    "dimension": "ISSUER_CONCENTRATION",
    "measured": "0.26",
    "threshold": "0.20",
    "recommended_action": "REDUCE_EXPOSURE",
    "evidence": { "policy_pack": "SG_DEFAULT/1.0.0" }
  }
]
```

---

## 7. Surveillance Signals (Operational + Risk)

These are *signals*, not hard breaches, and can route to monitoring dashboards.

### 7.1 Signal categories

* **Pattern**: repeated small trades (“trade slicing”), frequent cancels
* **Concentration jumps**: large delta in a single instrument/issuer
* **Liquidity stress**: increase in illiquid tiers
* **FX churn**: excessive FX conversion relative to net portfolio change
* **Order anomalies**: out-of-order dependencies, duplicate submissions, stale fills

Schema:

```json
"surveillance_signals": [
  {
    "signal_id": "SIG_FX_CHURN",
    "severity": "MEDIUM",
    "summary": "High FX turnover relative to portfolio delta",
    "details": {
      "fx_turnover_base": "250000.00",
      "portfolio_delta_base": "50000.00",
      "ratio": "5.0"
    }
  }
]
```

---

## 8. Exception Workflow (Stateless MVP + Persistent Option)

### 8.1 Exception object

```json
{
  "exception_id": "ex_...",
  "execution_id": "exec_...",
  "type": "RECON_MISMATCH|POLICY_BREACH|SURVEILLANCE_ALERT",
  "severity": "HIGH",
  "status": "OPEN|ACKNOWLEDGED|RESOLVED",
  "created_at": "...",
  "details": { ... },
  "recommended_actions": [
    { "code": "REQUEST_REVIEW", "text": "Escalate to compliance review." }
  ]
}
```

### 8.2 Persistence

If RFC-0014G is implemented, store exceptions in Postgres with append-only event history.

---

## 9. APIs

### 9.1 Compute post-trade checks (on-demand)

`POST /v1/executions/{execution_id}/post-trade/checks`

Body:

```json
{
  "policy_pack_id": "SG_DEFAULT",
  "policy_pack_version": "1.0.0",
  "portfolio_snapshot_after": { ... }  // optional if system can fetch
}
```

Response includes:

* post_trade_reconciliation
* post_trade_breaches
* surveillance_signals
* exceptions (if persisted) or suggested exceptions

### 9.2 Get exceptions

`GET /v1/exceptions?execution_id=&status=&severity=&limit=&cursor=`

### 9.3 Acknowledge/resolve exception

`POST /v1/exceptions/{exception_id}/transitions`

---

## 10. Observability (Ops-grade)

Metrics:

* reconciliation_runs_total{status=...}
* breaches_detected_total{dimension=..., severity=...}
* exceptions_open_total{severity=...}
* execution_dependency_violations_total
* post_trade_check_latency_ms

Logging must include:

* correlation_id
* execution_id
* proposal_id/version_no
* policy_pack_id/version

---

## 11. Testing Plan

Unit tests:

* reconciliation classification (matched/partial/mismatched)
* breach detection thresholds based on policy packs
* signal generation for canned scenarios

Integration tests:

* simulate an execution with partial fills and validate:

  * reconciliation = PARTIAL
  * no false mismatch
* simulate a post-trade issuer breach

Golden tests:

* optional: snapshot post-trade check outputs for demo scenarios

---

## 12. Acceptance Criteria (DoD)

* System can compute post-trade reconciliation from fills and/or portfolio snapshots.
* System detects post-trade policy breaches using policy packs.
* System generates surveillance signals deterministically.
* Exceptions are produced with standardized reason codes and suggested actions.
* Ops metrics and structured logs are available for monitoring.

---

## 13. Follow-ups

* Trade cost analysis (TCA)
* Regulatory reporting integration
* Cross-portfolio surveillance (client-level CIF monitoring)
* Automated remediation proposals (auto-generated unwind/rebalance suggestions)
 
