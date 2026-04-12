# RFC-0021 Slice 4 Evidence: Enterprise Suitability Policy Engine Core

- RFC: `docs/rfcs/RFC-0021-proposal-decision-summary-and-enterprise-suitability-policy.md`
- Slice Status: IMPLEMENTED
- Date: 2026-04-12
- Owner: `lotus-advise`

## Scope Delivered

Slice 4 upgraded the suitability engine from a flat scanner into a policy-versioned core that can evolve without duplicating business logic across routes, artifacts, or UI.

Implemented outcomes:

1. introduced a baseline suitability policy-pack seam inside the scanner,
2. split the scanner into modular evaluators for concentration, issuer, liquidity, governance, cash-band, and product-complexity evidence,
3. enriched `SuitabilityIssue` with enterprise policy metadata and remediation semantics,
4. persisted `policy_pack_id` and `policy_version` on suitability results and propagated the version into `proposal_decision_summary`,
5. classified complex-product evidence gaps as explicit suitability missing-evidence outcomes,
6. tightened decision-summary behavior so policy missing-evidence posture yields `INSUFFICIENT_EVIDENCE` ahead of generic review routing.

## Code Changes

### Richer Suitability Contract

`src/core/models.py`

Added enterprise-ready suitability fields:

1. `classification`,
2. `remediation`,
3. `approval_implication`,
4. `policy_pack_id`,
5. `policy_version`,
6. `PRODUCT` as a first-class suitability dimension,
7. result-level `policy_pack_id` and `policy_version`.

Result:

1. suitability issues now carry stable policy metadata,
2. replay and persistence surfaces preserve which policy pack produced the advisory posture,
3. later slices can classify approvals and material changes without inventing another side channel.

### Modular Policy-Pack Core

`src/core/common/suitability.py`

The scanner now uses a baseline policy pack with modular evaluator stages:

1. single-position concentration,
2. issuer concentration,
3. liquidity exposure,
4. governance restrictions,
5. cash band,
6. governance trade attempts,
7. product complexity evidence.

Result:

1. the logic is easier to extend dimension-by-dimension,
2. new policy overlays can reuse the same evaluator structure,
3. the scanner is no longer one monolithic pass that mixes policy metadata with issue projection.

### Product Complexity Evidence Gap

Complex products marked through shelf attributes now produce a distinct suitability issue:

1. `issue_id = MISSING_CLIENT_PRODUCT_COMPLEXITY_EVIDENCE`,
2. `dimension = PRODUCT`,
3. `classification = UNKNOWN_DUE_TO_MISSING_EVIDENCE`,
4. `approval_implication = CLIENT_CONTEXT_REQUIRED`.

Result:

1. complex-product recommendations no longer look like generic concentration or governance findings,
2. the system records that the gap is evidence completeness, not confirmed unsuitability,
3. Slice 5 can later replace the missing-evidence posture with true client-context evaluation once canonical client data is integrated.

### Decision Summary Alignment

`src/core/advisory/decision_summary.py`

Updated behavior:

1. `suitability_policy_version` now uses the persisted suitability result version,
2. suitability issues classified as `UNKNOWN_DUE_TO_MISSING_EVIDENCE` now become explicit `missing_evidence` entries,
3. `INSUFFICIENT_EVIDENCE` takes precedence over generic review routing for `PENDING_REVIEW` proposals when suitability missing-evidence exists,
4. primary reason code now favors missing-evidence reason codes when the overall decision posture is insufficient evidence.

Result:

1. the decision layer stays aligned with the enterprise policy output,
2. UI and replay consumers receive a truthful explanation for policy evidence gaps,
3. missing client/product evidence no longer appears as an ordinary review state.

## Tests Added Or Tightened

### Suitability Engine

`tests/unit/advisory/engine/test_engine_suitability_scanner.py`

Added or strengthened scenarios for:

1. policy pack/version persistence on suitability results,
2. medium concentration breach routing to `RISK_REVIEW`,
3. product complexity evidence gaps producing distinct `PRODUCT` issues with `UNKNOWN_DUE_TO_MISSING_EVIDENCE`,
4. approval implications carried by issue metadata.

### Decision Summary

`tests/unit/advisory/engine/test_engine_proposal_decision_summary.py`

Added a targeted scenario proving:

1. complex-product client-evidence gaps produce `INSUFFICIENT_EVIDENCE`,
2. the missing-evidence reason code becomes primary,
3. `suitability_policy_version` is propagated into the decision summary.

### Workflow And Persistence

`tests/unit/advisory/engine/test_engine_proposal_workflow_service.py`

Strengthened create-persistence assertions so:

1. persisted suitability results carry policy version metadata,
2. the decision summary uses the same suitability policy version.

### Workflow Gate Fixtures

`tests/unit/advisory/engine/test_engine_workflow_gates.py`

Updated fixtures to use the richer suitability issue contract so the gate tests remain contract-accurate.

## Validation

Full repository gate:

```powershell
make check
```

Result:

1. lint passed,
2. format passed,
3. mypy passed,
4. OpenAPI gate passed,
5. vocabulary inventory passed,
6. all `472` unit tests passed.

## Review Pass

The post-implementation review focused on whether the policy-pack seam was meaningful enough for future slices.

Decision:

1. keep one baseline pack in Slice 4 rather than inventing unused jurisdiction overlays,
2. keep evaluator logic modular now so Slice 5 and Slice 6 can plug in more evidence without rewriting the scanner,
3. avoid introducing a parallel policy engine API until a real consumer needs it.

## Remaining Work For Next Slice

Slice 5 should integrate canonical client, mandate, and richer product context so the current missing-evidence path can become true private-banking suitability evaluation.

Immediate next focus:

1. canonical client and mandate context inputs,
2. degraded-context handling from upstream authority,
3. restricted and eligible product overlays using authoritative context,
4. deterministic fixtures for stateful and lifecycle persistence paths.
