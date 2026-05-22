# RFC-0023 Slice 11B/11C: Report and Render Reviewed Narrative Realization

Status: implemented

Date: 2026-05-22

## Outcome

Slices 11B and 11C close the downstream report/render portion of RFC-0023 Slice 11. The
`lotus-advise` Slice 11A report-request package is now consumed by `lotus-report` and rendered by
`lotus-render` as an optional advisor-use advisory narrative page in the portfolio-review report
path.

This closure does not promote client-ready commentary, archive retention, Gateway composition,
Workbench rendering, data-product registration, trust telemetry, or `/platform/capabilities`
narrative support. Those remain gated by later implementation slices.

Slice 11D later closed the archive metadata-summary portion. This document remains the report and
render closure record.

## Implemented Behavior

`lotus-report` now:

1. accepts a typed `proposal_narrative_package` on report requests,
2. validates package shape, reviewed status, source hash, sections, disclosures, guardrails,
   limitations, lineage, and advisory execution-boundary evidence,
3. persists the reviewed package snapshot on the report job,
4. projects an immutable `reviewed_advisory_narrative` render payload into `report_data`,
5. preserves package lineage, review posture, policy version, disclosure refs, source hashes, and
   advisor-use restrictions in generated report data.

`lotus-render` now:

1. consumes `report_data.reviewed_advisory_narrative`,
2. omits the page unless the package status is `included`,
3. renders a portfolio-review v1 advisory narrative page with package lineage, review state, policy
   version, source hash, approved sections, disclosures, guardrail posture, limitations, and AI
   lineage where present,
4. keeps the narrative page explicitly advisor-use oriented rather than client-ready,
5. preserves the existing render contract when no reviewed advisory narrative is supplied.

## Evidence

`lotus-advise` Slice 11A:

- PR: `#148`
- Merge commit: `15dd3b66c685205c5917ed65fa58d417c70be370`
- Main Releasability Gate: run `26276265035`, green
- Wiki publication commit: `80d5ea4`

`lotus-report` Slice 11B:

- PR: `#94`
- Merge commit: `279a01fb0d3cb0ccf72ae2584309769b308228a8`
- Main Releasability Gate: run `26277926795`, green
- Wiki publication commit: `a3efa2c`

`lotus-render` Slice 11C:

- PR: `#13`
- Merge commit: `6995d3b350462e94ec4770712494eedbd32aec76`
- Main Releasability Gate: run `26279111418`, green
- Wiki publication commit: `adb1adc`

## Remaining Slice 11 Work

Still gated after the report/render closure:

- archive artifact realization, retention, lineage, and access-audit references until Slice 11D,
- `lotus-gateway` consumption of canonical narrative posture,
- Workbench consumption through Gateway/BFF only,
- browser validation for advisor, compliance, client-draft, blocked, degraded, and guardrail
  product-surface states,
- client-ready commentary and artifact export,
- data-product, trust-telemetry, and `/platform/capabilities` promotion.
