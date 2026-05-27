# RFC-0026 Slice 16: Implementation Proof

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0026: Advisor Cockpit Operating Workflow |
| **Slice** | 16 - implementation proof |
| **Status** | IMPLEMENTED - LIVE CANONICAL PROOF HARDENED |
| **Proof Date** | 2026-05-27 |
| **Owner** | `lotus-advise` with `lotus-gateway`, `lotus-workbench`, and `lotus-platform` evidence |
| **Implementation Branch** | `rfc0026-advisor-cockpit-gold-standard` |

## Proof Scope

Slice 16 proves the first-wave RFC-0026 advisor cockpit through the governed canonical
front-office runtime for `PB_SG_GLOBAL_BAL_001`.

The proof covers:

1. source-owned Advise cockpit action list, action detail, snapshot, preparation-packet,
   supportability, acknowledgement, and tactical house-view cohort flows,
2. Gateway publication of those routes without local workflow reconstruction,
3. Workbench canonical validation through Gateway-only APIs,
4. policy-review pending-review posture from the RFC-0025 canonical policy scenario,
5. blocked client-ready publication posture,
6. source-backed meeting-preparation packets,
7. source-backed tactical house-view impact action projection,
8. cursor pagination and invalid-cursor rejection,
9. compliance and DPM owner-role projection,
10. acknowledgement idempotency and replay-safe validation,
11. evidence refs, lineage refs, reason codes, priority, owner role, source scope, and supportability
    posture on returned actions.

## Canonical Evidence

The governed runtime command passed after the proof was hardened:

```powershell
npm run live:validate
```

Machine-readable evidence:

1. `lotus-workbench/output/playwright/live-canonical/live-validation-summary.json`
2. `ADVISOR_COCKPIT_ACTION_ACKNOWLEDGED`
3. `paginationCursor`
4. `roleProjectionValidated`
5. `houseViewCohortId`
6. `preparationPacketCount`
7. `preparationPacketRouteCount`
8. `clientReadyPublication: BLOCKED`
9. `supportabilityPosture: ADVISE_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED`
10. `workbenchPosture: CANONICAL_WORKBENCH_PROOF_PASSED_RFC0026`

Screenshot evidence remains paired with the machine-readable validation bundle under
`lotus-workbench/output/playwright/live-canonical/`. Screenshots alone are not accepted as cockpit
readiness proof.

## Live Defects Fixed At The Right Test Layer

The strengthened canonical validator exposed real implementation defects. Each defect was fixed at
the owning layer and pinned by a lower-level automated test before live validation was rerun.

| Defect | Owning fix | Regression coverage |
| --- | --- | --- |
| Stale Gateway image caused the new cockpit house-view route to return `404`. | `lotus-workbench` one-command canonical validation now passes `-BuildImages`. | `tests/unit/live-canonical-validation-script.test.ts` |
| Portfolio-scoped cockpit preparation omitted proposal records created by the canonical automation actor. | `lotus-advise` uses portfolio scope as the source boundary when a portfolio id is supplied. | `tests/unit/advisory/engine/test_engine_advisor_cockpit_service.py` |
| Memo/report-derived cockpit actions lost portfolio scope and escaped the requested canonical portfolio. | `lotus-advise` joins memo/report readiness sources back to proposal records before action construction. | `tests/unit/advisory/engine/test_engine_advisor_cockpit_source_read_model.py` and service tests |
| Source-backed tactical house-view cockpit actions returned no lineage refs. | `lotus-advise` carries `TacticalHouseViewAffectedCohort:v1` lineage and content hash into cockpit actions. | `tests/unit/advisory/engine/test_engine_advisor_cockpit_action_factory.py` |
| Execution-status and other source-backed cockpit actions could be emitted without lineage refs. | `lotus-advise` adds default source-action lineage for all source-backed cockpit actions. | `tests/unit/advisory/engine/test_engine_advisor_cockpit_action_factory.py` |

## Hardened Proof Assertions

`lotus-workbench/scripts/live/validation/advisor-cockpit-proof.mjs` now validates:

1. action-list portfolio scoping,
2. action-detail identity and version consistency,
3. every listed action has status, priority, owner role, reason codes, evidence refs, lineage refs,
   title, next action, and SLA age band,
4. cursor pagination returns a stable `next_cursor` and does not repeat the first item,
5. invalid cursors return the expected validation error,
6. compliance projection does not leak non-compliance owner roles,
7. DPM projection exposes `HOUSE_VIEW_IMPACT_REVIEW` when the canonical scenario seeds a
   source-backed house-view cohort,
8. preparation packets exist through both snapshot and preparation-packet route,
9. supportability and Workbench posture match the canonical contract,
10. acknowledgement is replay-safe and does not clear pending-review or blocked client-ready
    posture.

## Boundaries Preserved

This proof does not claim:

1. client-ready publication,
2. completed policy approval or sign-off authority,
3. CRM system-of-record behavior,
4. external client communication,
5. OMS orders, fills, settlement, or execution SOR behavior,
6. DPM campaign creation or portfolio-management ownership,
7. full RFC-0028 demo/RFP package readiness.

## Local Validation Evidence

Targeted checks run for this proof hardening:

1. `npm test -- --run tests/unit/advisor-cockpit-proof.test.ts`
2. `npm run live:validate`
3. `python -m ruff format src/core/advisor_cockpit/action_factory.py src/core/advisor_cockpit/service.py tests/unit/advisory/engine/test_engine_advisor_cockpit_action_factory.py`
4. `python -m ruff check src/core/advisor_cockpit/action_factory.py src/core/advisor_cockpit/service.py tests/unit/advisory/engine/test_engine_advisor_cockpit_action_factory.py`
5. `python -m pytest tests/unit/advisory/engine/test_engine_advisor_cockpit_action_factory.py tests/unit/advisory/engine/test_engine_advisor_cockpit_source_read_model.py tests/unit/advisory/engine/test_engine_advisor_cockpit_service.py -q`
6. `python -m mypy src/core/advisor_cockpit/action_factory.py src/core/advisor_cockpit/source_read_model.py src/core/advisor_cockpit/service.py`
7. `docker compose up -d --build` in `lotus-advise` before rerunning live validation after Advise
   source changes.

## Closure Posture

Slice 16 is implementation-proof complete on the feature branch. RFC-0026 final closure still
requires PR checks, stranded-truth reconciliation, merge to `main`, mainline validation, and wiki
publication where wiki source changed.
