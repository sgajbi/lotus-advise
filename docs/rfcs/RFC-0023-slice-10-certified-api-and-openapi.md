# RFC-0023 Slice 10: Certified API and OpenAPI Baseline

| Metadata | Details |
| --- | --- |
| RFC | RFC-0023 Grounded Advisory AI Narrative and Client-Ready Proposal Commentary |
| Slice | Slice 10 |
| Status | IMPLEMENTED - CERTIFIED API AND OPENAPI BASELINE |
| Implemented On | 2026-05-22 |
| Primary Repository | `lotus-advise` |
| Capability Posture | Certifies the existing additive advisor-review narrative API shape. It documents and tests the canonical artifact-path request field, proposal-version narrative review route, proposal lineage/replay routes, error responses, idempotency header guidance, stale-route absence, and material returned fields. It does not add standalone narrative read or regeneration endpoints, client-ready publication, report/render/archive inclusion, Gateway, Workbench, data-product telemetry, or `/platform/capabilities` promotion. |

## Outcome

Slice 10 closes the API-governance baseline for RFC-0023 advisor-review narrative without creating
duplicate route shapes. The implementation keeps narrative generation additive to the existing
proposal artifact and lifecycle inputs and keeps review/replay under the proposal-version route
family.

The certified route family is:

| Purpose | Canonical API posture |
| --- | --- |
| Narrative request | Additive `narrative_request` field on proposal artifact and lifecycle create/version payloads. |
| Narrative review | `POST /advisory/proposals/{proposal_id}/versions/{version_no}/narrative/review`. |
| Proposal lineage | `GET /advisory/proposals/{proposal_id}/lineage`. |
| Proposal replay | `GET /advisory/proposals/{proposal_id}/versions/{version_no}/replay-evidence`. |
| Async replay | `GET /advisory/proposals/operations/{operation_id}/replay-evidence`. |

Standalone narrative read and regeneration routes remain intentionally absent. Exact narrative JSON
is read through proposal-version detail and replay evidence until later slices implement broader
downstream consumption.

## OpenAPI Contract

Slice 10 tightens the public contract by documenting:

1. narrative review 404, 409, 422, and 503 response meanings,
2. proposal create/version response meanings where narrative request payloads are accepted,
3. lineage and replay response meanings for proposal and async replay evidence,
4. `Idempotency-Key` header guidance on narrative review,
5. schema descriptions and examples for narrative request, review, response, and replay evidence
   models,
6. stale-route absence for unsupported narrative read, regeneration, and lineage aliases.

## Behavior Certification

The certification tests prove:

1. a version without `proposal_narrative` returns `PROPOSAL_NARRATIVE_NOT_FOUND` with HTTP 422,
2. a missing proposal returns HTTP 404 from narrative review,
3. idempotency payload drift returns HTTP 409,
4. idempotent replay returns the same review identifier and marks the response as replayed,
5. replay evidence carries exact `proposal_narrative` and latest `proposal_narrative_review`
   material fields, including `source_narrative_hash`,
6. OpenAPI exposes only the canonical narrative review path and no stale narrative route aliases,
   with material returned-field coverage for narrative review and replay evidence.

## Non-Promoted Behavior

The following remain explicitly gated:

1. standalone narrative read endpoints,
2. standalone narrative regeneration endpoints,
3. compliance-review, client-draft, or client-ready narrative states,
4. report/render/archive artifact inclusion,
5. Gateway or Workbench rendering,
6. narrative data-product or trust-telemetry promotion,
7. `/platform/capabilities` narrative feature promotion,
8. sales/demo-safe narrative proof.

## Acceptance Gate

1. OpenAPI quality, API vocabulary, and no-alias gates must pass through the repository-native
   gate.
2. Endpoint certification covers behavior and every material narrative review field returned by the
   canonical route.
3. Stale or duplicate narrative route shapes remain absent from the generated OpenAPI contract.

## Next Slice

RFC-0023 may proceed to Slice 11 after this slice is merged and validated. Slice 11 should add
implementation-backed report/render/archive, Gateway, and Workbench realization only where the
canonical APIs certified here are consumed without local inference.
