# RFC-0023 Slice 11A: Reviewed Narrative Report-Request Package Propagation

Status: implemented

Date: 2026-05-22

## Outcome

Slice 11A implements the first bounded part of RFC-0023 Slice 11 inside `lotus-advise`: report
requests can explicitly propagate a reviewed, source-backed proposal narrative package to the
downstream `lotus-report` seam.

This slice does not claim full report rendering, archive publication, Gateway composition, or
Workbench rendering. Those remain gated by later Slice 11 increments.

## Implemented Behavior

`POST /advisory/proposals/{proposal_id}/report-requests` now accepts
`include_reviewed_narrative`.

When omitted or `false`, report requests preserve the existing behavior.

When `true`, `lotus-advise`:

1. loads exact proposal-version replay evidence,
2. requires a persisted proposal narrative for that immutable version,
3. requires the latest narrative review to be `APPROVED_FOR_ADVISOR_USE`,
4. verifies the review `source_narrative_hash` still matches the source narrative payload,
5. sends a compact `proposal_narrative_package` to the report seam,
6. persists a compact narrative package summary in the append-only `REPORT_REQUESTED` event,
7. exposes that package summary through delivery summary and replay evidence.

## Package Contents

The downstream report request receives:

- narrative identity, status, generation mode, audience, and policy version,
- review id, review state, client-ready status, reviewer, review timestamp, and source hash,
- source lineage hashes for request, artifact, and simulation,
- narrative sections, disclosures, guardrail results, limitations, and AI lineage,
- advisory execution-boundary evidence when execution posture already exists.

## Blocking Rules

The request is blocked before calling `lotus-report` when:

- the selected proposal version has no narrative,
- the selected proposal version has no narrative review,
- the latest review is not `APPROVED_FOR_ADVISOR_USE`,
- the review hash no longer matches the source narrative.

Guardrail and disclosure posture is carried in the package for downstream rendering and review; the
report request gate is the persisted review decision plus immutable hash continuity.

## Validation

Implemented tests prove:

- approved reviewed narrative packages are included in the report seam request,
- lineage hashes are present,
- delivery summary exposes the persisted package summary,
- unreviewed narrative report requests fail before downstream report invocation,
- existing report event projection behavior remains compatible.

Focused local validation:

```text
python -m pytest tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py::test_report_request_includes_only_approved_reviewed_narrative_package tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py::test_report_request_blocks_reviewed_narrative_without_approved_review tests/unit/advisory/engine/test_engine_proposal_reporting.py -q
```

## Remaining Slice 11 Work

Still gated:

- concrete `lotus-report`, `lotus-render`, and `lotus-archive` artifact realization,
- `lotus-gateway` consumption of canonical narrative posture,
- Workbench consumption through Gateway/BFF only,
- browser validation for advisor, compliance, client-draft, blocked, degraded, and guardrail
  product-surface states.
