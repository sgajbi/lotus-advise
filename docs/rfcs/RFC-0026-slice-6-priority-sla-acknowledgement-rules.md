# RFC-0026 Slice 6: Priority, SLA, and Acknowledgement Rules

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0026: Advisor Cockpit Operating Workflow |
| **Slice** | 6 - priority, next action, and SLA aging engine |
| **Status** | IMPLEMENTED - DETERMINISTIC SLA AND ACKNOWLEDGEMENT POSTURE |
| **Implemented Date** | 2026-05-27 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0026-advisor-cockpit-gold-standard` |
| **Capability Posture** | This slice implements pure core SLA aging and acknowledgement posture rules. It does not expose cockpit APIs, persist acknowledgement writes, promote cockpit data products, add Gateway/Workbench surfaces, or claim runtime advisor-cockpit support. Those remain mandatory subsequent RFC-0026 slices. |

## Decision

Slice 6 adds `src/core/advisor_cockpit/rules.py` as the rule layer for deterministic SLA aging and
acknowledgement posture.

This keeps the rules backend-owned before runtime APIs and Workbench surfaces exist:

1. due-time aging is deterministic from `due_at` and caller-supplied `now`,
2. missing due times produce `NOT_APPLICABLE`,
3. far future due times produce `NOT_DUE`,
4. due within 24 hours produces `DUE_SOON`,
5. due within the one-hour grace window produces `DUE_NOW`,
6. overdue items produce `OVERDUE` or `CRITICAL_OVERDUE`,
7. acknowledgement state can be attached without changing status, priority, or owner role,
8. owner-blocking posture remains true for `BLOCKED`, `PENDING_REVIEW`, and
   `HANDOFF_REQUESTED`.

## Implemented Core Contracts

| Contract | Responsibility |
| --- | --- |
| `derive_cockpit_sla_age_band` | Converts due-time posture into a deterministic SLA age band. |
| `with_cockpit_sla_age_band` | Applies derived SLA posture to an action item without changing identity or ownership. |
| `apply_cockpit_acknowledgement_state` | Attaches acknowledgement state without clearing blocking posture. |
| `is_cockpit_action_owner_blocking` | Identifies action statuses that still require owner attention. |
| `DUE_SOON_WINDOW` | 24-hour due-soon threshold. |
| `DUE_NOW_GRACE_WINDOW` | One-hour due-now grace threshold. |
| `CRITICAL_OVERDUE_WINDOW` | 24-hour critical-overdue threshold. |
| `OWNER_BLOCKING_STATUSES` | Backend-owned owner-blocking status set. |

## Boundary Controls

Slice 6 keeps the runtime claim boundary unchanged:

1. no acknowledgement API is exposed,
2. no acknowledgement persistence is added,
3. no stale-version write guard is added yet,
4. no Gateway or Workbench actioning contract is added,
5. no data product, trust telemetry, or `/platform/capabilities` claim is promoted,
6. canonical `RFC26_ADVISOR_COCKPIT_CANONICAL` proof remains blocked until backend, Gateway, and
   Workbench runtime behavior exists.

This is not deferral outside RFC-0026. It is the required pure rule layer before the runtime API
slice can safely add persisted acknowledgement writes, stale-version protection, audit events,
OpenAPI certification, and live proof.

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Deterministic SLA aging | Tests cover `NOT_APPLICABLE`, `NOT_DUE`, `DUE_SOON`, `DUE_NOW`, `OVERDUE`, and `CRITICAL_OVERDUE`. |
| Identity preservation | Tests prove applying SLA posture does not change action id, status, or priority. |
| Acknowledgement boundary | Tests prove acknowledgement does not clear `PENDING_REVIEW`, priority, owner role, or owner-blocking posture. |
| Non-blocking terminal states | Tests prove completed and superseded actions are not owner-blocking. |
| Non-promoting posture | RFC/wiki tests assert Slice 6 is indexed without advertising runtime cockpit support. |

Validation:

1. `python -m pytest tests/unit/advisory/engine/test_engine_advisor_cockpit_rules.py`
2. `python -m pytest tests/unit/test_rfc0026_slice6_priority_sla_rules_contract.py`
3. `python -m ruff check .`
4. `python -m ruff format --check .`

## Next Slice Handoff

Slice 7 can now add certified cockpit snapshot, action-list, action-detail, supportability, and
acknowledgement APIs with cursor pagination, entitlement projection, OpenAPI examples, error
models, stale-version protection, and audit behavior. Runtime support remains unpromoted until
the RFC-0026 API, persistence, Gateway, Workbench, mesh, and canonical proof slices are
implemented and validated.
