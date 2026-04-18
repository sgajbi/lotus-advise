# Proposal Lifecycle

## Core Model

The lifecycle surface persists advisory proposals as:

- one proposal aggregate
- immutable versions
- append-only workflow events
- structured approval records
- delivery and execution posture derived from workflow history

## What Creation Does

`POST /advisory/proposals` does more than storage. It:

1. runs advisory simulation,
2. builds the deterministic proposal artifact,
3. persists the first immutable version,
4. creates workflow audit history,
5. stores idempotency mapping.

## Versioning

New versions are created through `POST /advisory/proposals/{proposal_id}/versions`.

The model is immutable-by-version. A later version does not overwrite the earlier one. That keeps replay, support, and audit continuity intact.

## Transitions And Approvals

The lifecycle API separates:

- generic state transitions
- explicit approval recording

Approval and consent are structured workflow actions, not ad hoc annotations. The repository demo set includes grounded examples for:

- transition to compliance review
- client consent approval
- compliance approval
- transition to executed

## Delivery And Execution Posture

`lotus-advise` tracks advisory-owned delivery posture without taking over reporting or execution ownership.

It can:

- request a report payload through the `lotus-report` seam
- record an execution handoff
- ingest vendor-neutral execution updates
- expose delivery summary, delivery history, and execution status

It must not become the downstream execution system of record.

## Decision Summary And Alternatives

Persisted proposal surfaces expose backend-owned:

- `proposal_decision_summary`
- `proposal_alternatives`

These are part of the lifecycle evidence story and should remain tied to canonical upstream simulation and enrichment.
