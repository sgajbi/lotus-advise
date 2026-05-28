# API Surface

## Health

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

## Advisory Simulation

- `POST /advisory/proposals/simulate`
- `POST /advisory/proposals/artifact`

These endpoints accept normalized advisory input contracts and require `Idempotency-Key`. They are the core deterministic simulation and artifact entry points.

## Advisory Proposal Lifecycle

- `POST /advisory/proposals`
- `GET /advisory/proposals`
- `GET /advisory/proposals/{proposal_id}`
- `GET /advisory/proposals/{proposal_id}/versions/{version_no}`
- `POST /advisory/proposals/{proposal_id}/versions`
- `GET /advisory/proposals/{proposal_id}/versions/{version_no}/narrative`
- `POST /advisory/proposals/{proposal_id}/versions/{version_no}/narrative/regenerate`
- `POST /advisory/proposals/{proposal_id}/versions/{version_no}/narrative/review`
- `POST /advisory/proposals/{proposal_id}/transitions`
- `POST /advisory/proposals/{proposal_id}/approvals`
- `POST /advisory/proposals/{proposal_id}/report-requests`
- `POST /advisory/proposals/{proposal_id}/execution-handoffs`
- `POST /advisory/proposals/{proposal_id}/execution-updates`

Report requests support `include_reviewed_narrative=true` for RFC-0023 advisor-review narrative
package propagation. The request is blocked unless the selected immutable proposal version has a
persisted narrative, an `APPROVED_FOR_ADVISOR_USE` review, and matching source narrative hash.
Standalone narrative read returns exact persisted advisor-review narrative and latest review
posture. Standalone regeneration returns a non-persisted, review-required advisor-review candidate
from immutable version evidence and does not mutate proposal truth or publish client-ready
commentary.
Delivery evidence records the compact narrative package summary. `lotus-report` now consumes and
snapshots the reviewed package, and `lotus-render` renders it as an optional advisor-use
portfolio-review advisory narrative page. `lotus-archive` stores a support-safe archive metadata
summary for rendered advisor-use portfolio-review artifacts with approved review posture and source
hash lineage. `lotus-gateway` exposes product-facing reviewed-narrative posture from these
canonical advisory routes, and `lotus-workbench` renders the Gateway-backed advisor-use proposal
narrative posture. Client-ready publication remains gated.

## Advisory Operations And Support

- `GET /advisory/proposals/{proposal_id}/delivery-summary`
- `GET /advisory/proposals/{proposal_id}/delivery-events`
- `GET /advisory/proposals/{proposal_id}/execution-status`

These support surfaces derive operator-facing posture from append-only workflow history.
Execution handoff, execution-status, delivery-summary, and delivery-history payloads include
structured ownership-boundary evidence so operators can see that `lotus-advise` records advisory
handoff and status posture while the downstream execution provider remains the execution system of
record.

## Advisory Workspace

- `POST /advisory/workspaces`
- `GET /advisory/workspaces/{workspace_id}`
- `POST /advisory/workspaces/{workspace_id}/draft-actions`
- `POST /advisory/workspaces/{workspace_id}/evaluate`
- `POST /advisory/workspaces/{workspace_id}/save`
- `GET /advisory/workspaces/{workspace_id}/saved-versions`
- `GET /advisory/workspaces/{workspace_id}/saved-versions/{workspace_version_id}/replay-evidence`
- `POST /advisory/workspaces/{workspace_id}/resume`
- `POST /advisory/workspaces/{workspace_id}/compare`
- `POST /advisory/workspaces/{workspace_id}/assistant/rationale`
- `POST /advisory/workspaces/{workspace_id}/handoff`

## Tactical House View

- `POST /advisory/tactical-house-view/cohorts/evaluate`

This endpoint returns `TacticalHouseViewAffectedCohort:v1` for a governed bank-authored tactical
house-view instruction and caller-supplied source-backed candidate portfolios. It does not discover
the global portfolio universe, create rebalance waves, approve trades, or integrate with OMS.

## Advisor Cockpit

- `GET /advisory/cockpit/actions`
- `GET /advisory/cockpit/actions/{action_item_id}`
- `POST /advisory/cockpit/actions/{action_item_id}/acknowledgements`
- `GET /advisory/cockpit/snapshot`
- `GET /advisory/cockpit/supportability`

These RFC-0026 endpoints expose source-owned advisor operating workflow evidence for action items,
daily snapshot posture, supportability, and durable acknowledgement replay. Responses preserve
source refs, action reason codes, SLA posture, acknowledgement lineage, and unsupported-claim
boundaries. Acknowledgements are advisor workflow evidence only: they do not approve policy, clear
blockers, contact clients, create CRM tasks, or initiate OMS activity.

## Bank Demo Proof

- `GET /advisory/bank-demo-proof/scenario-contract`
- `GET /advisory/bank-demo-proof/supported-claim-register`
- `POST /advisory/bank-demo-proof/proof-packs`

These RFC-0028 endpoints expose the Advise-owned bank-demo proof contract for Gateway and Workbench
product consumption. The scenario contract fixes the canonical `PB_SG_GLOBAL_BAL_001` journey,
the supported-claim register maps each demo/RFP claim to implementation evidence, and proof-pack
capture writes sanitized runtime posture for repeatable validation.

`POST /advisory/bank-demo-proof/proof-packs` must fail with HTTP 409 when material proof fields
drift from the supported-claim register. Runtime posture rejects runtime base URLs that carry
credentials, query strings, or fragments; proof artifact refs reject URL/query/fragment/traversal
and sensitive token/secret/prompt/raw-payload material; HTTP 422 validation responses do not echo
rejected sensitive input; summaries redact secrets, tokens, prompts, raw payloads, trace IDs, and
correlation IDs; endpoint evidence records bounded integer `latency_ms` values.

The proof APIs do not approve client-ready publication, external client communication,
bank-specific attestations, legal/regulatory advice, completed sign-off/approval, or
OMS/order/fill/settlement. Gateway and Workbench must consume this source-owned contract rather
than reconstructing advisory suitability, memo, narrative, policy, or proof semantics locally.

## Contract Notes

- OpenAPI is the governed external contract.
- REST remains the current contract posture; this service does not justify gRPC today.
- Lifecycle and support routes can be feature-gated by runtime flags.
- Tactical house-view cohorts preserve source refs and supportability posture rather than
  recalculating source-owned portfolio facts locally.
- Readiness should fail closed when required upstream execution authority is not correctly configured.
- `GET /platform/capabilities` includes `advise.observability.advisory_supportability`,
  `advisory.proposals.reviewed_narrative_evidence`, and the
  `advisory_proposal_reviewed_narrative_evidence` workflow for advisor-review narrative evidence.
  The capability wording remains bounded: compliance-review, client-draft, client-ready
  publication, and client communication are not promoted. Canonical Workbench proof is now covered
  by the live runtime suite and the governed `proposal.narrative_posture` panel proof rather than
  by `/platform/capabilities`.
- `GET /platform/capabilities` includes `advisory.proposals.memo_evidence_pack` and
  `advisory_proposal_memo_evidence_pack` for RFC-0024 advisor-use memo evidence. The workflow
  depends on lifecycle, reporting, and `lotus-report` readiness, and it does not promote
  client-ready memo publication, external client communication, or full bank-demo/RFP package
  claims.
- `GET /platform/capabilities` includes `advisory.advisor_cockpit` and
  `advisor_cockpit_operating_workflow` for RFC-0026 first-wave advisor cockpit evidence after
  Advise, Gateway, Workbench, and canonical `PB_SG_GLOBAL_BAL_001` proof. The wording remains
  bounded to advisor operating workflow evidence and does not promote client-ready publication,
  external client communication, CRM system-of-record behavior, OMS lifecycle, completed policy
  approval authority, or full RFC-0028 demo/RFP package claims.
- RFC-0028 bank-demo proof is exposed through `/advisory/bank-demo-proof/*`, not through a
  generic capability toggle. Supported demo claims must be backed by the supported-claim register,
  proof-pack evidence, and runtime posture artifacts before they are reused in demo, RFP, security,
  or commercial material.
- `GET /platform/capabilities` also includes a bounded `supportability` summary for advisory
  readiness, degraded dependency posture, and lifecycle-disabled posture. The
  `supportability.metric_labels` field documents the exact bounded label tuple for
  `lotus_advise_advisory_supportability_total`.
- Dependency readiness entries include `runtime_probe_enabled`, `readiness_basis`, and
  `degraded_reason` so operators can distinguish missing configuration, configuration-only
  non-production posture, successful runtime probes, and failed runtime probes without exposing
  dependency base URLs.
- Execution posture entries include `execution_ownership` evidence with advisory role,
  downstream system-of-record, and ownership-boundary labels for audit, support, and pre-sales
  explanation.
