# RFC-0023 Slice 10B: Standalone Narrative Read and Regeneration API

Status: Implemented on 2026-05-22

Owning RFC: `RFC-0023`

Owner repository: `lotus-advise`

## Purpose

Slice 10B closes the remaining owner-side standalone narrative API gap from Slice 10. It adds
explicit read and regeneration routes under the canonical proposal-version route family without
creating duplicate route shapes or mutating immutable proposal versions.

This slice does not promote compliance-review narrative, client-draft narrative, client-ready
commentary, data-product posture, trust telemetry, canonical demo screenshot proof, or
`/platform/capabilities` narrative support.

## Implemented Route Family

The canonical standalone narrative route family is now:

1. `GET /advisory/proposals/{proposal_id}/versions/{version_no}/narrative`
2. `POST /advisory/proposals/{proposal_id}/versions/{version_no}/narrative/regenerate`
3. `POST /advisory/proposals/{proposal_id}/versions/{version_no}/narrative/review`

The read route returns the exact `proposal_narrative` persisted on the immutable proposal-version
artifact, the latest narrative review when present, the canonical source narrative hash, the replay
evidence path, and an explicit read-only posture.

The regeneration route builds a non-persisted advisor-review candidate from the immutable proposal
artifact. It returns current and regenerated narrative hashes, source artifact and request hashes,
latest review posture, material-change posture, and explicit `NOT_PERSISTED_REVIEW_REQUIRED`
status. It does not replace the persisted narrative, does not append workflow history, and does
not publish client-ready commentary.

## OpenAPI And Contract Additions

This slice adds documented OpenAPI request and response models for standalone narrative reads and
regeneration candidates. The read response carries the persisted narrative, latest review, source
hash, replay evidence path, and read-only posture. The regeneration request captures advisor
identity, reason, section scope, generation mode, jurisdiction, product types, and client audience.
The regeneration response carries current and candidate narratives, source hashes, material-change
posture, latest review, and explicit non-persistence posture.

## Behavioral Guarantees

1. Read is exact and read-only; it never calls narrative generation.
2. Regeneration does not mutate the immutable proposal version or append workflow events.
3. Regeneration candidates remain gated for advisor review and are not client-ready commentary.
4. Missing proposal versions return `PROPOSAL_NOT_FOUND`; versions without persisted narrative
   return `PROPOSAL_NARRATIVE_NOT_FOUND`.

## Acceptance Review

| Gate | Result | Evidence |
| --- | --- | --- |
| Read route returns exact persisted narrative | Pass | API test proves read returns the same narrative id and latest review without calling regeneration |
| Regeneration is non-persistent | Pass | API test proves regenerated candidate can differ while the persisted narrative remains unchanged on reread |
| Missing narrative behavior is explicit | Pass | API test proves read and regeneration return `PROPOSAL_NARRATIVE_NOT_FOUND` with HTTP 422 when the version has no narrative |
| Missing proposal behavior is explicit | Pass | API test proves missing proposal returns HTTP 404 |
| OpenAPI is documented | Pass | Contract tests assert request/response schema docs, route refs, summaries, descriptions, and error responses |
| Immutable evidence lineage is preserved | Pass | Response carries source request hash, artifact hash, persisted narrative hash, regenerated hash, and replay-evidence path |

## Remaining Gates

The following RFC-0023 claims remain gated until later implementation slices close with tests,
documentation, and publication evidence:

1. compliance-review narrative,
2. client-draft narrative,
3. client-ready commentary and publication,
4. narrative data-product declaration and catalog posture,
5. trust-telemetry fixture and validation,
6. canonical demo screenshot proof for populated proposal narrative journeys,
7. `/platform/capabilities` narrative support promotion.
