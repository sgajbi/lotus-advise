# RFC-0023 Slice 11D: Archive Reviewed Narrative Artifact Realization

Status: implemented

Date: 2026-05-22

## Outcome

Slice 11D closes the archive portion of RFC-0023 Slice 11. `lotus-archive` now stores a support-safe
`reviewed_advisory_narrative` metadata summary for portfolio-review documents whose rendered PDF
already includes the advisor-use reviewed advisory narrative page from the `lotus-report` and
`lotus-render` path.

This closure does not promote client-ready commentary, data-product registration, trust telemetry,
or `/platform/capabilities` narrative support. Gateway composition and Workbench rendering are
tracked separately and were later closed by Slice 11E.

## Implemented Behavior

`lotus-archive` now:

1. accepts an optional `reviewed_advisory_narrative` metadata summary on archived portfolio-review
   documents,
2. validates the archive summary against report/render posture so unsupported or client-ready
   narrative claims cannot be archived,
3. requires `report_type=portfolio_review`, `template_id=portfolio-review`,
   `review_state=APPROVED_FOR_ADVISOR_USE`, `audience=ADVISOR_REVIEW`, and
   `included_in_render=true`,
4. requires narrative and package hashes to use explicit `sha256:` provenance,
5. rejects `CLIENT_READY` and `READY_FOR_CLIENT` narrative statuses,
6. records source events with a
   `reviewed_advisory_narrative_archive_summary_preserved` reason code and a
   `reviewed_advisory_narrative_package` artifact reference,
7. exposes the supported feature in the archive service profile without storing raw narrative
   sections separately.

## Evidence

`lotus-archive` Slice 11D:

- Implementation PR: `#26`
- Implementation merge commit: `30eeabeef703587930828ae92a340626056b1ab3`
- CI repair PR: `#27`
- Main commit after repair: `ddc45bad456fb2f2e0d13a0ab2a2d4972010b36d`
- Main Releasability Gate: run `26281218904`, green
- Wiki publication commit: `9888480`
- Wiki check: `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-archive`, `DiffCount 0`
- Local validation: `make check`, `make ci`, and `git diff --check`

## Remaining Slice 11 Work

Still gated:

- `lotus-gateway` consumption of canonical narrative posture,
- Workbench consumption through Gateway/BFF only,
- browser validation for advisor, compliance, client-draft, blocked, degraded, and guardrail
  product-surface states,
- client-ready commentary and artifact export,
- data-product, trust-telemetry, and `/platform/capabilities` promotion.
