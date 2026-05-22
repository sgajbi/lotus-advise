# RFC-0023 Slice 11E: Gateway and Workbench Reviewed Narrative Realization

Status: Implemented on 2026-05-22

Owning RFC: `RFC-0023`

Owner repositories: `lotus-advise`, `lotus-gateway`, `lotus-workbench`

## Purpose

Slice 11E closes the product-facing Gateway and Workbench portion of RFC-0023 Slice 11 for
advisor-use reviewed narrative posture. The slice does not promote client-ready commentary,
compliance-review narrative, client-draft narrative, data-product posture, trust telemetry,
canonical demo screenshot proof, or `/platform/capabilities` narrative support. Standalone
narrative read/regeneration APIs are tracked separately and later closed by Slice 10B.

## Implemented Behavior

`lotus-gateway` now exposes reviewed-narrative posture through canonical `lotus-advise` APIs:

1. `POST /api/v1/proposals/{proposal_id}/versions/{version_no}/narrative/review`
2. `POST /api/v1/proposals/{proposal_id}/report-requests`
3. `GET /api/v1/proposals/{proposal_id}/delivery-summary`
4. `GET /api/v1/proposals/{proposal_id}/delivery-events`

Gateway preserves the advisory source boundary. It composes product-facing posture from
`lotus-advise` review, report-request, delivery-summary, and delivery-event responses and does not
reconstruct narrative facts locally.

`lotus-workbench` now renders the Gateway-backed advisor-use proposal narrative posture on the
direct proposal detail route:

1. `/proposals/{proposalId}` renders a proposal detail view instead of redirecting away.
2. The `ProposalNarrativePosturePanel` displays review posture, report-package readiness,
   delivery posture, source hash continuity, guardrail posture, limitations, and delivery events
   from Gateway/BFF data.
3. Workbench keeps client-contact, render, and archive actions out of the advisor-use narrative
   posture panel until client-ready publication is implemented.

## Evidence

`lotus-gateway` implementation evidence:

1. PR: https://github.com/sgajbi/lotus-gateway/pull/241
2. Merge commit: `9fd7de9e3a654645e0dab3e9f05ea4cbcb84ea40`
3. Main Releasability Gate: run `26283131587`, green
4. Wiki publication commit: `844ee43`
5. Wiki check: `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-gateway` returned `DiffCount 0`
6. Local targeted proof: `python -m pytest tests/unit/test_proposal_service.py tests/unit/test_upstream_clients.py tests/integration/test_proposals_router.py tests/contract/test_proposals_contract.py -q` returned 210 passed
7. Local repo gate: `make check` returned 581 passed
8. Local CI gate: `make ci` returned 772 passed, 88.50 percent coverage, and no `pip-audit`
   vulnerabilities

`lotus-workbench` implementation evidence:

1. PR: https://github.com/sgajbi/lotus-workbench/pull/349
2. Merge commit: `0609b2f040af5bb0de913ec86bfe259ba842b302`
3. Main Releasability Gate: run `26284505488`, green
4. Wiki check after publication: `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-workbench`
   returned `DiffCount 0`
5. Local typecheck: `npm run typecheck` passed
6. Focused proposal narrative posture tests: 15 passed
7. Local repo gate: `make check` passed with 251 test files, 1063 tests, 90.43 percent coverage,
   and a green Next.js build
8. Local e2e gate: `make test-e2e` passed with 4 passed and 7 skipped under the current smoke
   configuration

## Acceptance Review

| Gate | Result | Evidence |
| --- | --- | --- |
| Gateway consumes canonical `lotus-advise` narrative endpoints | Pass | Gateway PR #241 adds reviewed-narrative review, report-request, delivery-summary, and delivery-event composition over Advise APIs |
| Gateway avoids local narrative reconstruction | Pass | Gateway service composes posture from upstream responses and keeps Advise as source authority |
| Workbench consumes Gateway/BFF only | Pass | Workbench PR #349 adds proposal narrative posture API helpers and view model over Gateway-backed proposal APIs |
| Workbench avoids local narrative inference | Pass | The panel renders review posture, package readiness, delivery posture, hash continuity, guardrails, limitations, and events from response fields |
| Client-ready actions remain blocked | Pass | Workbench exposes advisor-use posture only and omits client-contact, render, and archive action controls |
| Owner truth updated | Pass | `lotus-advise` README, RFC index, wiki source, and repository context now distinguish implemented Gateway/Workbench posture from remaining gates |

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
