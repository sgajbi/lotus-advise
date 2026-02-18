# RFC-0014H: Jurisdiction & Policy Packs (Suitability, Disclosures, and Gating Rules)

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
| **Created** | 2026-02-18 |
| **Target Release** | MVP-14H |
| **Depends On** | RFC-0014D (Suitability Scanner v1), RFC-0014E (Proposal Artifact), RFC-0014F (GateDecision) |
| **Recommended** | RFC-0014G (Persistence) for full auditability across jurisdictions |
| **Doc Location** | `docs/rfcs/RFC-0014H-jurisdiction-policy-packs.md` |
| **Backward Compatibility** | Not required |

---

## 0. Executive Summary

RFC-0014H introduces **Jurisdiction Policy Packs** to make the advisory proposal system production-grade across regions (e.g., SG, HK, CH, UK, EU).

A Policy Pack is a versioned configuration bundle that defines:

1) **Suitability thresholds and rules** (what to check, severity mapping)
2) **Disclosure templates** (required text blocks and product-doc requirements)
3) **Workflow gating policy** (what triggers risk/compliance review)
4) **Reporting artifacts** (required sections for a proposal depending on jurisdiction)

This makes the engine:
- consistent
- auditable
- configurable without code changes
- extensible as regulations and internal rules evolve

---

## 1. Motivation / Problem Statement

Private banking is multi-jurisdictional. The same portfolio proposal must satisfy:

- different regulatory requirements,
- internal policy differences (house rules),
- varying disclosure obligations,
- differing risk/compliance gating thresholds.

Hardcoding those rules in code is brittle and slow. Instead, we need policy packs that can be:
- versioned
- reviewed
- tested
- rolled out per jurisdiction and business unit

---

## 2. Scope

### 2.1 In Scope
- Define `PolicyPack` schema and loading mechanism.
- Add `policy_pack_id` and `policy_pack_version` to requests/options.
- Apply policy packs to:
  - Suitability scanner thresholds and severity mapping
  - Proposal artifact disclosure requirements
  - GateDecision evaluation thresholds
- Provide a minimal built-in pack set:
  - `SG_DEFAULT` (Singapore baseline)
  - `GLOBAL_DEFAULT` (fallback)

### 2.2 Out of Scope
- Full legal/regulatory interpretation and mapping
- Real-time policy management UI
- External policy distribution and approvals system (can be added later)
- Localization (language translations) beyond placeholders

---

## 3. Terminology

### 3.1 Jurisdiction
A jurisdiction is a regulatory region or booking center that influences suitability and disclosures.

Examples:
- `SG` (Singapore)
- `HK`
- `CH`
- `UK`
- `EU`

### 3.2 Policy Pack
A versioned bundle that fully defines:
- suitability policy
- gating policy
- disclosure policy
- artifact requirements

---

## 4. PolicyPack Schema (Config-as-Code)

Store policy packs as JSON/YAML in repo (for MVP):
- `policy_packs/<jurisdiction>/<pack_id>/<version>.json`

Example path:
- `policy_packs/SG/SG_DEFAULT/1.0.0.json`

### 4.1 PolicyPack top-level
```json
{
  "pack_id": "SG_DEFAULT",
  "pack_version": "1.0.0",
  "jurisdiction": "SG",
  "effective_from": "2026-01-01",
  "effective_to": null,

  "suitability_policy": { ... },
  "gating_policy": { ... },
  "disclosure_policy": { ... },
  "artifact_policy": { ... }
}
````

---

## 5. Suitability Policy

### 5.1 Thresholds

```json
"suitability_policy": {
  "thresholds": {
    "single_position_max_weight": "0.10",
    "issuer_max_weight": "0.20",
    "cash_band": { "min": "0.01", "max": "0.05" },
    "liquidity_caps": {
      "L4": "0.10",
      "L5": "0.05"
    }
  },
  "severity_mapping": {
    "single_position": {
      "over_cap": "MEDIUM",
      "over_cap_125pct": "HIGH"
    },
    "issuer": {
      "over_cap": "HIGH"
    },
    "liquidity": {
      "L5_over_cap": "HIGH",
      "L4_over_cap": "MEDIUM"
    }
  },
  "enabled_checks": [
    "SINGLE_POSITION",
    "ISSUER_CONCENTRATION",
    "LIQUIDITY_EXPOSURE",
    "GOVERNANCE",
    "CASH_BAND",
    "DATA_QUALITY"
  ]
}
```

### 5.2 Governance policy

```json
"governance_policy": {
  "banned_behavior": "FORCE_LIQUIDATION|FREEZE",
  "sell_only_buy_behavior": "BLOCK|WARN",
  "restricted_buy_behavior": "WARN|ALLOW",
  "suspended_behavior": "FREEZE|BLOCK"
}
```

---

## 6. Workflow Gating Policy

Defines how GateDecision is derived from:

* rule_results
* suitability issues (NEW/RESOLVED/PERSISTENT)

```json
"gating_policy": {
  "blocked_if": {
    "any_hard_rule_fail": true,
    "missing_fx": true,
    "missing_prices": true
  },
  "compliance_review_if": {
    "new_high_suitability_issue": true,
    "governance_violation": true
  },
  "risk_review_if": {
    "new_medium_suitability_issue": true,
    "any_soft_rule_fail": true
  },
  "client_consent_if": {
    "status_ready": true,
    "no_reviews_required": true
  }
}
```

This policy pack provides the deterministic decision thresholds while your code provides the stable algorithm.

---

## 7. Disclosure Policy

Defines required disclosure blocks and product-document requirements.

### 7.1 Disclosure blocks

```json
"disclosure_policy": {
  "required_blocks": [
    "GENERAL_RISK_DISCLAIMER",
    "MARKET_DATA_SNAPSHOT_ASSUMPTION",
    "COSTS_NOT_INCLUDED",
    "TAX_NOT_INCLUDED"
  ],
  "optional_blocks": [
    "FX_RISK_DISCLAIMER",
    "CONCENTRATION_RISK_DISCLAIMER",
    "LIQUIDITY_RISK_DISCLAIMER"
  ],
  "block_texts": {
    "GENERAL_RISK_DISCLAIMER": "Investments may go down as well as up...",
    "FX_RISK_DISCLAIMER": "FX rates may move adversely..."
  }
}
```

### 7.2 Product docs

```json
"product_doc_requirements": {
  "required_doc_types": ["FACTSHEET", "KID"],
  "by_product_type": {
    "STRUCTURED_NOTE": ["TERM_SHEET", "RISK_DISCLOSURE"]
  }
}
```

The Proposal Artifact must include a `product_docs` section listing required docs per instrument.

---

## 8. Artifact Policy

Defines what sections must exist in the Proposal Artifact for the jurisdiction.

```json
"artifact_policy": {
  "required_sections": [
    "SUMMARY",
    "PORTFOLIO_IMPACT",
    "TRADES_AND_FUNDING",
    "ASSUMPTIONS_AND_LIMITS",
    "DISCLOSURES",
    "EVIDENCE_BUNDLE"
  ],
  "optional_sections": [
    "DRIFT_ANALYSIS",
    "SUITABILITY_SUMMARY"
  ],
  "rendering_hints": {
    "max_top_contributors": 5,
    "max_top_weight_changes": 10
  }
}
```

---

## 9. Policy Pack Loading and Resolution

### 9.1 Request integration

Add to `options`:

* `policy_pack_id` (optional)
* `policy_pack_version` (optional)
* `jurisdiction` (optional, can also come from portfolio/mandate metadata)

Resolution order:

1. explicit `policy_pack_id+version` (if provided)
2. `jurisdiction` default pack
3. `GLOBAL_DEFAULT`

### 9.2 Validation

On startup:

* load all policy packs from repo folder
* validate schema and version format
* fail-fast if invalid

At runtime:

* if requested pack missing -> 400 Problem Details (`POLICY_PACK_NOT_FOUND`)
* if version invalid -> 400

---

## 10. Implementation Plan

1. Define `PolicyPack` Pydantic models
2. Implement policy pack loader:

   * directory scan
   * schema validation
   * caching in memory
3. Wire policy pack into:

   * Suitability scanner thresholds and enabled checks
   * GateDecision engine mapping
   * Proposal artifact disclosure blocks and required sections
4. Add minimal packs:

   * `GLOBAL_DEFAULT/1.0.0`
   * `SG_DEFAULT/1.0.0`
5. Tests:

   * loader tests
   * policy resolution tests
   * golden tests ensuring disclosures and gates differ by policy pack

---

## 11. Testing Plan

### 11.1 Unit tests

* policy pack schema validation
* resolution order
* missing pack returns 400 Problem Details
* enabled_checks toggle behavior (check excluded => no issues emitted)

### 11.2 Golden scenarios

* `scenario_14H_policy_pack_global.json`
* `scenario_14H_policy_pack_sg.json`

Assert that for the same proposal:

* suitability thresholds differ (e.g., issuer cap)
* resulting gate differs if thresholds trigger
* disclosure blocks differ (e.g., FX risk block required for SG)

---

## 12. Acceptance Criteria (DoD)

* Policy packs load at startup and are validated.
* Requests can specify policy pack; otherwise jurisdiction defaults apply.
* Suitability outputs, gating outputs, and disclosure blocks are driven by the policy pack.
* At least two policy packs exist and demonstrate different outcomes in tests.
* All behavior remains deterministic and auditable.

---

## 13. Follow-ups

* External policy pack distribution (S3, registry)
* Policy approvals workflow (four-eyes)
* Localization for disclosures (en, zh, etc.)
* Jurisdiction-specific suitability mappings (client profile → allowed products)

 