# RFC-0027 Slice 9 - Certified Advise APIs and OpenAPI

Status: IMPLEMENTED - ADVISE API SURFACE ONLY

## Outcome

Slice 9 exposes the governed advisory copilot through `lotus-advise` APIs. The API surface is
action-specific, evidence-packet backed, review-gated, idempotent where mutation occurs, and
OpenAPI documented. At Slice 9 time it did not expose Gateway routes, Workbench surfaces,
canonical front-office proof, data-product promotion, or client-ready publication. Later RFC-0027
closure slices now implement Gateway, Workbench, canonical proof, and the bounded
`AdvisoryCopilotInteractionRecord:v1` data-product promotion. Client-ready publication remains
blocked.

Implemented endpoints:

1. `POST /advisory/copilot/evidence-packets`
2. `POST /advisory/copilot/evidence-packets/from-proposal-version`
3. `GET /advisory/copilot/evidence-packets/{evidence_packet_id}`
4. `POST /advisory/copilot/actions`
5. `GET /advisory/copilot/actions/{run_id}`
6. `POST /advisory/copilot/actions/{run_id}/reviews`
7. `GET /advisory/copilot/supportability`
8. `GET /advisory/proposals/{proposal_id}/versions/{version_id}/copilot-runs`

No free-form prompt endpoint exists.

## API Posture

The API owns advisory copilot orchestration in Advise:

1. evidence-packet creation uses the deterministic redaction/projection builder,
2. Workbench-safe proposal-version projection lets callers request source-owned evidence by
   proposal/version/action family without constructing source sections in the browser,
3. action execution loads a persisted evidence packet and calls the approved `lotus-ai`
   workflow-pack adapter,
4. run persistence records hashes, guardrails, review posture, lineage, tenant, caller, and
   correlation id,
5. proposal-version run history uses bounded newest-first keyset pagination with invalid-cursor
   rejection,
6. review actions are idempotent and audited,
7. supportability explicitly blocks client-ready publication, policy approval/sign-off authority,
   order/fill/settlement authority, and Gateway/Workbench promotion claims.

The API rejects raw prompt/provider/unsafe-output storage through the Slice 8 persistence guard.
`user_instruction` is allowed only as bounded request input for guardrail evaluation and hashed
audit lineage; the raw value is not persisted in the run record.

## Persistence Extension

Slice 9 adds durable evidence-packet records and migration
`src/infrastructure/postgres_migrations/advisory_copilot/0002_evidence_packet_records.sql`.
Follow-on hardening adds
`src/infrastructure/postgres_migrations/advisory_copilot/0003_copilot_run_version_pagination_indexes.sql`
for indexed proposal-version run history.

The migrations support:

1. evidence-packet readback,
2. proposal/portfolio scoped operational lookup,
3. proposal-version scoped copilot run history without unbounded repository reads,
4. repeatable API and Gateway/Workbench validation.

## Validation Evidence

Targeted commands:

1. `python -m ruff check src/core/advisory_copilot/records.py src/core/advisory_copilot/repository.py src/core/advisory_copilot/service.py src/core/advisory_copilot/api_models.py src/core/advisory_copilot/__init__.py src/infrastructure/advisory_copilot src/api/proposals/routes_advisory_copilot.py src/api/proposals/router.py src/api/main.py tests/unit/advisory/api/test_api_advisory_copilot.py`
2. `python -m pytest tests/unit/advisory/api/test_api_advisory_copilot.py -q`
3. `python scripts/openapi_quality_gate.py`
4. `python scripts/no_alias_contract_guard.py`
5. `python scripts/api_vocabulary_inventory.py --validate-only`

Implementation-backed tests cover:

1. evidence-packet create/read,
2. source-owned proposal-version evidence-packet projection for Workbench-safe consumption,
3. unsupported-evidence projection,
4. action run persistence and idempotent replay,
5. no raw user instruction persisted in API readback,
6. review action idempotency,
7. proposal-version run lookup with bounded keyset pagination,
8. invalid cursor rejection,
9. OpenAPI registration and absence of free-form prompt endpoints.

## Historical Slice 9 Boundary

This slice certified Advise APIs only. The remaining Gateway, Workbench, canonical
seed/automation, data-mesh promotion, live front-office proof, and polished product-surface work is
closed by `docs/rfcs/RFC-0027-slice-10-14-product-realization-proof-closure.md`. Client-ready
publication, external client communication, policy approval/sign-off authority, OMS order
lifecycle, fills, settlement, and full RFC-0028 demo/RFP claims remain outside the RFC-0027
supported claim.
