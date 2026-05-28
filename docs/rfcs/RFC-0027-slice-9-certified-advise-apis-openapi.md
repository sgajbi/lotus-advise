# RFC-0027 Slice 9 - Certified Advise APIs and OpenAPI

Status: IMPLEMENTED - ADVISE API SURFACE ONLY

## Outcome

Slice 9 exposes the governed advisory copilot through `lotus-advise` APIs. The API surface is
action-specific, evidence-packet backed, review-gated, idempotent where mutation occurs, and
OpenAPI documented. It does not expose Gateway routes, Workbench surfaces, canonical front-office
proof, data-product promotion, or client-ready publication. Those remain mandatory later RFC-0027
slices.

Implemented endpoints:

1. `POST /advisory/copilot/evidence-packets`
2. `GET /advisory/copilot/evidence-packets/{evidence_packet_id}`
3. `POST /advisory/copilot/actions`
4. `GET /advisory/copilot/actions/{run_id}`
5. `POST /advisory/copilot/actions/{run_id}/reviews`
6. `GET /advisory/copilot/supportability`
7. `GET /advisory/proposals/{proposal_id}/versions/{version_id}/copilot-runs`

No free-form prompt endpoint exists.

## API Posture

The API owns advisory copilot orchestration in Advise:

1. evidence-packet creation uses the deterministic redaction/projection builder,
2. action execution loads a persisted evidence packet and calls the approved `lotus-ai`
   workflow-pack adapter,
3. run persistence records hashes, guardrails, review posture, lineage, tenant, caller, and
   correlation id,
4. review actions are idempotent and audited,
5. supportability explicitly blocks client-ready publication, policy approval/sign-off authority,
   order/fill/settlement authority, and Gateway/Workbench promotion claims.

The API rejects raw prompt/provider/unsafe-output storage through the Slice 8 persistence guard.
`user_instruction` is allowed only as bounded request input for guardrail evaluation and hashed
audit lineage; the raw value is not persisted in the run record.

## Persistence Extension

Slice 9 adds durable evidence-packet records and migration
`src/infrastructure/postgres_migrations/advisory_copilot/0002_evidence_packet_records.sql`.

The migration supports:

1. evidence-packet readback,
2. proposal/portfolio scoped operational lookup,
3. repeatable API and future Gateway/Workbench validation.

## Validation Evidence

Targeted commands:

1. `python -m ruff check src/core/advisory_copilot/records.py src/core/advisory_copilot/repository.py src/core/advisory_copilot/service.py src/core/advisory_copilot/api_models.py src/core/advisory_copilot/__init__.py src/infrastructure/advisory_copilot src/api/proposals/routes_advisory_copilot.py src/api/proposals/router.py src/api/main.py tests/unit/advisory/api/test_api_advisory_copilot.py`
2. `python -m pytest tests/unit/advisory/api/test_api_advisory_copilot.py -q`
3. `python scripts/openapi_quality_gate.py`
4. `python scripts/no_alias_contract_guard.py`
5. `python scripts/api_vocabulary_inventory.py --validate-only`

Implementation-backed tests cover:

1. evidence-packet create/read,
2. unsupported-evidence projection,
3. action run persistence and idempotent replay,
4. no raw user instruction persisted in API readback,
5. review action idempotency,
6. proposal-version run lookup,
7. OpenAPI registration and absence of free-form prompt endpoints.

## Remaining RFC-0027 Boundary

This slice certifies Advise APIs only. Gateway, Workbench, canonical seed/automation, data-mesh
promotion, live front-office proof, and polished user-facing product surfaces remain inside
RFC-0027 and must be implemented before the advisory copilot becomes a supported product feature.
