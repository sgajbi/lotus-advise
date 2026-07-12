# RFC-0026 Slice 7: Certified Advise APIs

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0026: Advisor Cockpit Operating Workflow |
| **Slice** | 7 - snapshot and action-item APIs |
| **Status** | IMPLEMENTED - ADVISE BACKEND API SUPPORT |
| **Implemented Date** | 2026-05-27 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0026-advisor-cockpit-gold-standard` |
| **Capability Posture** | This slice exposes Advise-owned cockpit APIs and persistent acknowledgement writes. It does not promote Gateway, Workbench, data products, trust telemetry, `/platform/capabilities`, or client-demo claims. Those remain mandatory subsequent RFC-0026 slices. |

## Decision

Slice 7 promotes the first RFC-0026 runtime surface inside `lotus-advise` only. The implementation
keeps business logic out of controllers by adding `AdvisorCockpitService` and a dedicated
`AdvisorCockpitRepository` protocol. FastAPI route handlers are thin request/response adapters.

Implemented routes:

| Route | Method | Purpose |
| --- | --- | --- |
| `/advisory/cockpit/actions` | `GET` | Lists source-backed cockpit actions with cursor pagination. |
| `/advisory/cockpit/actions/{action_item_id}` | `GET` | Returns one source-backed action with evidence, lineage, owner, and unsupported-capability posture. |
| `/advisory/cockpit/snapshot` | `GET` | Returns a bounded operating snapshot with action counts, top actions, and supportability posture. |
| `/advisory/cockpit/supportability` | `GET` | Returns support-safe API/downstream/data-product readiness posture. |
| `/advisory/cockpit/actions/{action_item_id}/acknowledgements` | `POST` | Records an idempotent acknowledgement without clearing blocking posture. |

## Implementation Notes

Slice 7 adds:

1. `src/core/advisor_cockpit/service.py` for source-backed action listing, snapshot construction,
   supportability, and acknowledgement orchestration,
2. `src/core/advisor_cockpit/api_models.py` for request/response contracts with descriptions and
   examples,
3. `src/core/advisor_cockpit/persistence.py` for acknowledgement and idempotency records,
4. `src/core/advisor_cockpit/repository.py` for the cockpit repository boundary,
5. `src/api/proposals/routes_advisor_cockpit.py` for thin FastAPI routes,
6. `src/infrastructure/postgres_migrations/proposals/0008_cockpit_acknowledgements.sql` for
   durable acknowledgement and idempotency tables,
7. in-memory and Postgres repository implementations for acknowledgement persistence,
8. batch memo source reads through `list_memos_for_proposals` so snapshot/action construction stays
   bounded as proposal pages grow.

## API Quality and Boundary Controls

The API slice intentionally keeps these boundaries explicit:

1. action priority, status, owner role, reason codes, SLA, source refs, evidence refs, lineage refs,
   and unsupported capabilities are backend-owned,
2. acknowledgement is idempotent and stale-version protected,
3. acknowledgement does not clear `BLOCKED`, `PENDING_REVIEW`, owner role, priority, or
   client-ready blocked posture,
4. cursor pagination uses the existing RFC-0026 default 25 and maximum 100 limits,
5. source loading is bounded by `COCKPIT_SOURCE_LIMIT` and uses batch memo reads instead of
   per-proposal memo lookups,
6. supportability states Gateway, Workbench, data-product promotion, client-ready publication, and
   external communication as gated until implementation-backed slices land,
7. OpenAPI documents acknowledgement idempotency, stale-version validation, not-found behavior, and
   conflict behavior,
8. `/platform/capabilities` remains unpromoted for advisor cockpit because product-surface and
   canonical proof are not complete yet.

Current hardening note: Advisor Cockpit caller role and advisor scope are no longer accepted as
query parameters. The route family resolves actor, role, tenant, legal entity, capabilities,
authorized advisor scope, and authorized portfolio scope from trusted gateway/service headers before
source loading or acknowledgement persistence. Acknowledgement writes bind `acknowledged_by` to the
trusted actor before idempotency hashing and audit metadata are recorded.

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Thin controllers | Route tests validate API behavior while business rules live in `AdvisorCockpitService`. |
| Source-backed list/snapshot | Service tests prove policy, memo, and meeting-preparation actions are derived from source records. |
| Idempotency and stale-version protection | Service and API tests prove acknowledgement replay, idempotency conflict, and stale-version rejection. |
| OpenAPI quality | API tests prove cockpit routes are present and descriptions preserve Gateway/Workbench and acknowledgement boundaries. |
| Persistent acknowledgement store | In-memory and Postgres repositories implement cockpit acknowledgement and acknowledgement-idempotency records. |
| Bounded source reads | Service and repository tests prove memo evidence is loaded through one batch source-read path. |
| No premature product claim | Supported-features/wiki wording stays explicit that Gateway, Workbench, data products, canonical proof, and full product support remain mandatory RFC-0026 work. |

Validation:

1. `python -m pytest tests/unit/advisory/engine/test_engine_advisor_cockpit_service.py`
2. `python -m pytest tests/unit/advisory/api/test_api_advisor_cockpit.py`
3. `python -m pytest tests/unit/advisory/api/test_api_integration_capabilities.py`
4. `python -m ruff check .`
5. `python -m ruff format --check .`

## Next Slice Handoff

Slice 8 can now implement Gateway publication for the Advise cockpit APIs, preserving the Advise
contract without reinterpreting action status, policy posture, memo blockers, acknowledgement
semantics, or unsupported capabilities. Workbench and canonical automation remain blocked until the
Gateway slice is implemented and validated.
