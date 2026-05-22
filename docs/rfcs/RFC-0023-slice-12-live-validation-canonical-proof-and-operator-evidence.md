# RFC-0023 Slice 12: Live Validation, Canonical Proof, and Operator Evidence

Status: Implemented on 2026-05-22

Owning RFC: `RFC-0023`

Owner repositories: `lotus-advise`, `lotus-workbench`, `lotus-platform`

## Purpose

Slice 12 closes the implementation-backed proof gap for advisor-review proposal narrative. It
extends live validation so the supported narrative path is exercised through authoritative stateful
portfolio context, persisted proposal versions, standalone narrative read, non-persistent
regeneration, advisor-use review, reviewed report-package request, replay evidence, and canonical
Workbench proof.

This slice does not promote compliance-review narrative, client-draft narrative, client-ready
commentary, client-ready publication, or client-contact behavior.

## Implemented Behavior

`lotus-advise` stateful proposal create and version requests can now carry an optional
`stateful_input.narrative_request`. The request is applied after Lotus Core resolves the
authoritative portfolio context, so live narrative proof no longer needs to fall back to a legacy
stateless-only path.

The sequential live runtime suite now emits a structured `proposal_narrative` proof snapshot with:

1. proposal id, version number, narrative id, generation mode, and policy status,
2. persisted guardrail posture from immutable proposal-version narrative read,
3. non-persistent regeneration posture,
4. advisor-use review state, client-ready status, and source narrative hash,
5. reviewed report-package inclusion or degraded report-package state,
6. replay-evidence review state,
7. deterministic local guardrail-failure reproduction for unsupported claims,
8. optional AI-assisted narrative validation when
   `LOTUS_ADVISE_VALIDATE_AI_ASSISTED_NARRATIVE=1` is enabled,
9. live latency for the narrative proof path.

`lotus-workbench` canonical validation now creates a Gateway-backed proposal for
`PB_SG_GLOBAL_BAL_001` with an advisor-review `narrative_request`, exercises the
`/proposals/{proposalId}` narrative posture panel, records advisor-use review, requests reviewed
report packaging, verifies source narrative hash visibility, and captures governed screenshot
evidence under `proposal.narrative_posture`.

`lotus-platform` panel registry now includes `proposal.narrative_posture`, owned by
`lotus-advise`, with governed screenshot name `proposal-narrative-posture-live.png`.

## Acceptance Review

| Gate | Result | Evidence |
| --- | --- | --- |
| Deterministic narrative live validation has no AI dependency | Pass | `scripts/validate_cross_service_parity_live.py` creates stateful narrative proposals with `DETERMINISTIC_TEMPLATE` |
| Advisor-use read, regeneration, review, replay, and report package are validated | Pass | `LiveProposalNarrativeSnapshot` records read source, regeneration persistence, review state, source hash, replay state, and report package posture |
| AI-assisted mode is bounded | Pass | Optional live validation runs only when `LOTUS_ADVISE_VALIDATE_AI_ASSISTED_NARRATIVE=1`; otherwise evidence records `SKIPPED_NOT_ENABLED` |
| AI-unavailable fallback does not break core flow | Pass | Deterministic proof is the default path and optional AI proof accepts deterministic fallback lineage when configured |
| Guardrail failure path is observable and reproducible | Pass | `validate_guardrail_failure_path()` exercises production guardrail policy against unsupported-claim text and emits failing guardrail ids |
| Canonical Workbench proof is governed | Pass | Workbench live validator registers and screenshots `proposal.narrative_posture` through the RFC-0077 panel registry |
| Client-ready and client-draft remain gated | Pass | Live proof records `client_ready_status=NOT_REQUESTED`; docs and wiki continue to exclude client-ready and client-draft support |

## Local Validation

Targeted validation for this slice:

1. `python -m pytest tests/unit/advisory/api/test_live_runtime_suite.py tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py::test_stateful_create_can_request_advisor_review_narrative tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py::test_stateful_version_can_request_fresh_advisor_review_narrative -q`
2. `python -m ruff check scripts/validate_cross_service_parity_live.py scripts/live_runtime_proposal_narrative.py scripts/live_runtime_suite_artifacts.py src/core/proposals/input_models.py src/core/proposals/context.py tests/unit/advisory/api/test_live_runtime_suite.py tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py tests/e2e/live/test_live_runtime_suite.py`
3. `npm run test -- --run tests/unit/live-canonical-validation-script.test.ts tests/unit/proposal-narrative-posture-panel.test.tsx` in `lotus-workbench`
4. `npm run lint` in `lotus-workbench`
5. `python -m pytest tests/unit/test_rfc_0077_panel_registry_contract.py tests/unit/test_canonical_dpm_demo_story.py -q` in `lotus-platform`

Full closure additionally requires:

1. `make check` in `lotus-advise`,
2. repo-native Workbench and platform checks for the cross-repo proof changes,
3. governed canonical front-office validation against the running stack,
4. wiki drift check and publication after merge.

## Remaining Gates

The following RFC-0023 claims remain gated until later implementation slices close with tests,
documentation, and publication evidence:

1. compliance-review narrative,
2. client-draft narrative,
3. client-ready commentary and publication,
4. external client communication.
