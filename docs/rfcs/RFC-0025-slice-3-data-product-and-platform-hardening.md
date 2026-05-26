# RFC-0025 Slice 3: Data Product and Platform Hardening

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0025: Enterprise Suitability and Best-Interest Policy Packs |
| **Slice** | 3 - data product and platform hardening |
| **Status** | IMPLEMENTED - PROPOSED/BLOCKED DATA PRODUCT; NO POLICY SUPPORT PROMOTED |
| **Implemented Date** | 2026-05-26 |
| **Owner** | `lotus-advise`; `lotus-platform` generated catalog automation |
| **Implementation Branch** | `rfc25-slice3-data-product-hardening` |
| **Capability Posture** | This slice declares `AdvisoryPolicyEvaluationRecord:v1` as a governed proposed product with blocked trust telemetry. It does not implement policy-pack catalog, evaluation, persistence, review queues, report/sign-off packages, Gateway/Workbench policy surfaces, or client-ready policy publication. |

## Decision

RFC-0025 needs a governed policy-evaluation product boundary before runtime policy work starts.
That boundary must be visible to mesh governance without implying that advisors can evaluate,
approve, waive, publish, or communicate policy outcomes.

Slice 3 therefore creates a proposed, blocked data-product posture:

1. `AdvisoryPolicyEvaluationRecord:v1` is declared in
   `contracts/domain-data-products/lotus-advise-products.v1.json`,
2. blocked trust telemetry exists in
   `contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json`,
3. the product has no `current_routes` because no policy evaluation API exists yet,
4. `/platform/capabilities` does not advertise policy support,
5. catalog generation is validated from repo-native declarations so platform discovery can pick up
   the product after the declaration reaches `main`.

## Data Product Posture

| Control | Slice 3 posture |
| --- | --- |
| Product identity | `lotus-advise:AdvisoryPolicyEvaluationRecord:v1` |
| Lifecycle status | `proposed` |
| Product family | `workflow_and_decision_state` |
| Freshness class | `event_driven` |
| Completeness default | `blocked` |
| Lineage | Required, but not materialized until policy evaluation evidence exists |
| Evidence bundle | Required for eventual advisor/compliance use |
| Approved consumers | `lotus-gateway`, `lotus-report`, `lotus-render`, `lotus-archive`, `lotus-workbench`, `lotus-ai` |
| Current routes | None in this slice |
| Capability promotion | Forbidden until policy evaluation APIs, persistence, replay, Gateway/Workbench consumption, and proof are implemented |

## Trust Telemetry Posture

The RFC-0025 telemetry snapshot is intentionally blocked:

1. `freshness_state` is `unknown`,
2. `completeness_status` is `blocked`,
3. `data_quality_status` is `quality_unknown`,
4. `lineage.lineage_materialized` is `false`,
5. `blocking.blocked` is `true` with `RFC0025_POLICY_EVALUATION_RUNTIME_NOT_IMPLEMENTED`.

This is the correct enterprise posture. The policy-evaluation product is now a governed planning
and control object, but it is unavailable to business consumers until policy packs, source evidence,
evaluation, persistence, replay, review actions, sign-off packages, downstream consumption, and
front-office proof are implemented.

## Platform Hardening Posture

| Platform concern | Slice 3 decision |
| --- | --- |
| Catalog and dependency graph | Tests generate a current platform discovery catalog from repo-native declarations and validate policy telemetry against it. Platform generated artifacts should be refreshed after the Advise declaration is on `main`. |
| Certification report | Certification remains non-promotional because the product is proposed, blocked, and route-less. |
| SLO/access/evidence policy | Active mesh SLO/access/evidence policy files are deferred until the first supported policy API/data-product promotion slice. |
| Mesh certification | Existing required first-wave products remain the blocking mesh gate; this proposed product must not imply supported policy readiness. |
| `/platform/capabilities` | No policy row is added. Capability promotion is allowed only after implementation-backed policy runtime support exists. |

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Stranded-truth reconciliation | `git fetch origin --prune` and `git branch -r --no-merged origin/main` returned no unmerged remote branches before Slice 3 implementation. |
| Producer declaration | Added proposed `AdvisoryPolicyEvaluationRecord:v1` to `contracts/domain-data-products/lotus-advise-products.v1.json`. |
| Trust telemetry | Added blocked `contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json`. |
| Catalog automation | `tests/unit/test_trust_telemetry.py` generates a current platform domain-product catalog from repo-native declarations before running the platform trust-telemetry validator. |
| Capability non-promotion | Tests assert the product has no current routes and `/platform/capabilities` does not advertise policy evaluation support. |
| Documentation truth | RFC/wiki/supported-feature truth keeps policy-pack support planned until implementation-backed slices close. |

## Wiki And README Decision

Wiki source is updated because RFC implementation status, mesh/data-product posture, and
operator-facing supported-feature truth changed. README does not change in this slice because
runtime commands and supported API entrypoints did not change.
