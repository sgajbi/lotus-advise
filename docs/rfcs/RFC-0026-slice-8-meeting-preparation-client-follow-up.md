# RFC-0026 Slice 8: Meeting Preparation and Client Follow-Up

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0026: Advisor Cockpit Operating Workflow |
| **Slice** | 8 - meeting preparation, client follow-up, and advisor actioning |
| **Status** | IMPLEMENTED - SOURCE-BACKED ADVISE API SUPPORT |
| **Implemented Date** | 2026-05-27 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0026-advisor-cockpit-gold-standard` |

## Decision

Slice 8 makes meeting-preparation and client follow-up behavior first-class Advise-owned cockpit
output instead of leaving it embedded in a generic snapshot. The implementation remains source
backed and support safe:

1. meeting-preparation packets are projected from active proposal lifecycle evidence,
2. `GET /advisory/cockpit/preparation-packets` exposes a paginated preparation-packet API,
3. client follow-up actions are derived from `AWAITING_CLIENT_CONSENT` proposal state,
4. follow-up actions preserve the external communication and CRM boundaries,
5. Gateway and Workbench must render the Advise contract without reconstructing suitability,
   memo, narrative, policy, CRM, calendar, or client-communication semantics locally.

## Implementation Evidence

| Area | Evidence |
| --- | --- |
| Preparation packet API | `AdvisorCockpitService.list_preparation_packets` and `/advisory/cockpit/preparation-packets`. |
| Pagination and cursor validation | `ADVISOR_COCKPIT_PREPARATION_CURSOR_INVALID` service behavior and OpenAPI route coverage. |
| Source-backed packet construction | `_preparation_packets` projects `MeetingPreparationActionSource` evidence into support-safe packet sections. |
| Client follow-up actions | `ClientFollowUpActionSource` and `build_client_follow_up_action`. |
| Boundary controls | Unsupported capabilities include `EXTERNAL_CLIENT_COMMUNICATION` and `CRM_SYSTEM_OF_RECORD`. |
| API vocabulary governance | `docs/standards/api-vocabulary/lotus-advise-api-vocabulary.v1.json` includes the preparation-packet route. |

Validation:

1. `python -m pytest tests/unit/advisory/engine/test_engine_advisor_cockpit_service.py tests/unit/test_rfc0026_slice7_advise_api_contract.py -q`
2. `python scripts/openapi_quality_gate.py`
3. `python -m pytest tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py -q`
4. `python scripts/api_vocabulary_inventory.py`
5. `python scripts/api_vocabulary_inventory.py --validate-only`
6. `python -m ruff check ...`
7. `python -m mypy src/core/advisor_cockpit/api_models.py src/core/advisor_cockpit/service.py src/api/proposals/routes_advisor_cockpit.py`

## Claim Boundary

This slice does not add calendar scheduling, CRM system-of-record behavior, external client
communication, client-ready publication, or completed approval authority. Those remain explicitly
blocked unless later implementation-backed RFC slices prove them.
