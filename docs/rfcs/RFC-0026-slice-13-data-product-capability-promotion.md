# RFC-0026 Slice 13: Data Product and Capability Promotion

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0026: Advisor Cockpit Operating Workflow |
| **Slice** | 13 |
| **Status** | IMPLEMENTED - DATA PRODUCT AND CAPABILITY PROMOTION |
| **Date** | 2026-05-27 |
| **Owner** | `lotus-advise` |

## Purpose

Earlier RFC-0026 slices deliberately kept advisor-cockpit data products and `/platform/capabilities`
unpromoted until the Advise APIs, Gateway route family, Workbench surface, and canonical
front-office proof existed. Those prerequisites are now implemented and validated for
`PB_SG_GLOBAL_BAL_001`, so this slice promotes the source-owned cockpit supportability truth.

## Implemented

1. `AdvisorCockpitOperatingSnapshot:v1` is active in
   `contracts/domain-data-products/lotus-advise-products.v1.json`.
2. `AdvisoryActionItemRegister:v1` is active in the same declaration.
3. Trust telemetry snapshots exist for both products under `contracts/trust-telemetry/`.
4. `/platform/capabilities` advertises `advisory.advisor_cockpit` and
   `advisor_cockpit_operating_workflow`.
5. Advisor cockpit supportability now reports Gateway support, Workbench canonical proof, active
   data-product posture, and the canonical `PB_SG_GLOBAL_BAL_001` proof marker.

## Boundaries Preserved

The promotion is bounded to advisor operating workflow evidence. It does not claim:

1. client-ready publication,
2. external client communication,
3. CRM system-of-record behavior,
4. OMS orders, fills, or settlement,
5. completed policy approval or waiver authority,
6. full RFC-0028 demo/RFP package support.

## Evidence

1. Advise RFC-0026 API, service, capability, declaration, and trust telemetry tests.
2. Gateway RFC-0026 route and service tests.
3. Workbench canonical live validation for `PB_SG_GLOBAL_BAL_001`, including
   `ADVISOR_COCKPIT_ACTION_ACKNOWLEDGED` and `advisory-advisor-cockpit-live.png`.
4. Platform canonical data and panel registry tests for the RFC-0026 scenario and
   `advisory.advisor_cockpit`.
