# RFC-0023 Slice 3: Current-State Assessment and Narrative Contract Baseline

| Field | Value |
| --- | --- |
| **RFC** | RFC-0023 Grounded Advisory AI Narrative and Client-Ready Proposal Commentary |
| **Slice** | 3 |
| **Status** | IMPLEMENTED - CONTRACT BASELINE ONLY |
| **Implemented On** | 2026-05-22 |
| **Primary Repo** | `lotus-advise` |
| **Capability Posture** | This slice does not implement generated proposal narrative. It defines the additive contract baseline and confirms current evidence ownership before Slice 4 and Slice 5 implementation. |

## Outcome

Slice 3 maps the current implementation surfaces that can ground future proposal narrative and
defines the first additive contract baseline. It deliberately avoids adding public routes,
capability rows, persistence, or narrative generation code.

The current system already has enough deterministic evidence to support a first advisor-review
narrative in a later slice, but it is not yet safe to expose narrative because review ownership,
data-product posture, and persistence/replay semantics are still gated by later RFC-0023 slices.

## Current-State Evidence Map

| Surface | Current implementation evidence | Narrative relevance |
| --- | --- | --- |
| Proposal artifact | `src/core/advisory/artifact.py`, `src/core/advisory/artifact_models.py`, `tests/unit/advisory/engine/test_engine_proposal_artifact.py` | Supplies deterministic artifact sections, hashes, gate decision, decision summary, alternatives, and evidence bundle. |
| Proposal detail and versions | `src/core/proposals/response_models.py`, `src/core/proposals/service.py`, `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` | Supplies immutable proposal version detail, current version, request hash, artifact hash, simulation hash, and persisted evidence bundle. |
| Workspace evidence | `src/core/workspace/assistant_evidence.py`, `src/core/workspace/models.py`, `tests/unit/advisory/api/test_workspace_assistant_evidence.py` | Supplies evaluated workspace rationale evidence only; it is not proposal narrative authority. |
| Lifecycle and review state | `src/core/proposals/lifecycle_command.py`, `src/core/proposals/response_models.py`, `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` | Supplies append-only workflow events, approvals, current proposal state, and idempotent replay for state transitions and approvals. |
| Replay evidence | `src/core/replay/models.py`, `src/core/replay/service.py`, `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py` | Supplies normalized subject, hashes, continuity, and preserved evidence for proposal/workspace/async replay. |
| RFC-0021 decision summary | `src/core/advisory/decision_summary.py`, `src/core/advisory/decision_summary_models.py`, `tests/unit/advisory/engine/test_engine_proposal_decision_summary.py` | Supplies decision status, next action, confidence, missing evidence, material changes, approval requirements, and source refs. |
| RFC-0022 alternatives | `src/core/advisory/alternatives_projection.py`, `src/core/advisory/alternatives_models.py`, `tests/unit/advisory/engine/test_engine_proposal_alternatives.py` | Supplies ranked alternatives, rejected candidates, selected alternative posture, policy ids, and evidence refs. |
| Gateway and Workbench needs | RFC-owned future consumer boundary; no `lotus-gateway` or `lotus-workbench` change in this slice | Consumers need backend-owned narrative state and must not infer narrative facts locally. |

## Deterministic Evidence Available Now

Future advisor-review narrative may use these deterministic inputs when present:

1. proposal identifiers, version numbers, lifecycle origin, current state, and source workspace id,
2. request hash, simulation hash, artifact hash, and replay continuity,
3. proposal status, gate decision, and recommended next step,
4. decision status, primary reason code, primary summary, confidence, material changes, missing
   evidence, approval requirements, client/mandate posture, risk posture, and advisor action items,
5. proposal alternatives, selected alternative, rejected candidates, and alternatives evidence refs,
6. artifact evidence bundle, source refs, risk-lens posture, and context-resolution metadata,
7. workflow events, approvals, report-request posture, execution-handoff posture, and execution
   status where already persisted.

Future narrative must not infer:

1. suitability, mandate fit, best-interest posture, disclosures, fees, conflicts, or client consent
   beyond available deterministic evidence,
2. report/render/archive readiness before downstream proof exists,
3. DPM campaign or execution truth owned by `lotus-manage`,
4. client-ready approval where human review and disclosure posture are missing,
5. AI run posture where a proposal-narrative workflow pack has not executed.

## Additive Narrative Contract Baseline

The first implementation contract must be additive under the existing advisory proposal API family.
No public API v2 is required.

Proposed first endpoint family:

| Operation | Shape | Purpose |
| --- | --- | --- |
| Request deterministic narrative | `POST /advisory/proposals/{proposal_id}/narrative-requests` | Build or retrieve an advisor-review narrative for a specific proposal version from deterministic evidence. |
| Read narrative | `GET /advisory/proposals/{proposal_id}/narratives/{narrative_id}` | Return the persisted or transient narrative envelope, sections, guardrail posture, source refs, and review state. |
| Replay narrative | `GET /advisory/proposals/{proposal_id}/narratives/{narrative_id}/replay` | Return exact replay evidence for persisted narrative versions without model calls. |

Later endpoint families may add review actions, regeneration, AI-assisted workflow-pack execution,
Gateway consumption, report/render/archive packaging, and Workbench UI support only after later
slices implement their owning controls.

## Request Baseline

`ProposalNarrativeRequest` should use canonical snake_case fields:

| Field | Required | Baseline rule |
| --- | --- | --- |
| `proposal_version_no` | yes | Narrative is version-scoped; defaulting to current version may be added only if replay semantics remain explicit. |
| `audience` | yes | One of the allowed audience values below. |
| `sections` | yes | Non-empty ordered list of allowed section keys. |
| `requested_by` | yes | Actor id for audit and review traceability. |
| `idempotency_key` | yes at API boundary | Required for stateful generation or persisted narrative requests. |
| `correlation_id` | optional header | Propagated through logs, supportability, and AI adapter when used. |
| `generation_mode` | yes | `DETERMINISTIC_TEMPLATE` initially; `AI_ASSISTED_DRAFT` remains gated. |
| `review_intent` | yes | `ADVISOR_REVIEW` initially; client-facing intents remain gated. |

## Response Baseline

`ProposalNarrativeResponse` should return:

| Field | Purpose |
| --- | --- |
| `narrative_id` | Stable id when persisted; deterministic transient ids are acceptable only before persistence is added. |
| `proposal_id` and `proposal_version_no` | Version-scoped source identity. |
| `status` | Narrative readiness state from the allowed statuses below. |
| `audience` | Requested audience. |
| `generation_mode` | Deterministic or future AI-assisted generation mode. |
| `review_state` | Current human-review posture. |
| `sections` | Ordered narrative sections with section key, title, text, source refs, limitation refs, and guardrail refs. |
| `source_refs` | Canonical refs into proposal, artifact, evidence bundle, decision summary, alternatives, lifecycle, replay, and workflow events. |
| `input_hashes` | Request, simulation, artifact, evidence, and narrative-input hashes where available. |
| `guardrail_result` | Structured allowed/blocked/degraded posture with reason codes. |
| `lineage` | Policy version, template version, optional AI workflow-pack refs, requested_by, generated_at, and correlation id. |
| `limitations` | Explicit missing evidence and client-ready blockers. |

## Allowed Vocabulary

Audiences:

| Value | First-slice posture |
| --- | --- |
| `ADVISOR_REVIEW` | First implementation target. |
| `COMPLIANCE_REVIEW` | Proposed; requires policy/review controls. |
| `INVESTMENT_DESK_REVIEW` | Proposed; requires review workflow. |
| `CLIENT_DRAFT` | Gated; requires disclosure and approval posture. |
| `CLIENT_READY` | Gated; requires human approval, disclosure, report/render/archive, and replay proof. |

Sections:

| Value | Evidence source |
| --- | --- |
| `EXECUTIVE_SUMMARY` | Proposal status, gate decision, decision summary. |
| `RECOMMENDATION_RATIONALE` | Decision summary, artifact, proposed actions. |
| `RISK_AND_CONCENTRATION` | Risk lens and decision risk posture. |
| `SUITABILITY_AND_MANDATE` | Decision summary posture and explicit missing evidence. |
| `MATERIAL_CHANGES` | Decision-summary material changes. |
| `ALTERNATIVES_CONSIDERED` | RFC-0022 alternatives and rejected candidates. |
| `APPROVALS_AND_NEXT_STEPS` | Workflow events, approvals, gate decision, advisor action items. |
| `LIMITATIONS_AND_DISCLOSURES` | Missing evidence, unavailable sources, disclosure blockers. |

Statuses:

| Value | Meaning |
| --- | --- |
| `READY_FOR_ADVISOR_REVIEW` | Deterministic advisor-review narrative was generated and has required source refs. |
| `PENDING_REVIEW` | Narrative exists but requires bounded human review before downstream use. |
| `BLOCKED_BY_MISSING_EVIDENCE` | Required source evidence is missing. |
| `BLOCKED_BY_POLICY` | Policy/disclosure/review posture blocks requested audience or section. |
| `DEGRADED_SOURCE_LIMITED` | Narrative is available with explicit degraded-source limitations. |
| `REJECTED_BY_GUARDRAIL` | Output failed unsupported-claim or unsafe wording validation. |

Review states:

| Value | Meaning |
| --- | --- |
| `NOT_REQUIRED` | Deterministic advisor-only output that is not downstream-consumable. |
| `AWAITING_ADVISOR_REVIEW` | Advisor must review before downstream use. |
| `AWAITING_COMPLIANCE_REVIEW` | Compliance review is required. |
| `APPROVED_FOR_INTERNAL_USE` | Approved for internal advisor/compliance workflows only. |
| `APPROVED_FOR_CLIENT_DRAFT` | Approved for client draft only; not client-ready. |
| `APPROVED_FOR_CLIENT_READY` | Gated future state; requires later report/render/archive and approval proof. |
| `REJECTED` | Review rejected the narrative. |
| `SUPERSEDED` | A newer narrative replaces this version. |

## API Vocabulary Reconciliation

This slice does not change OpenAPI or API vocabulary inventory because no public narrative endpoint
or model is introduced. The baseline uses canonical snake_case field names and the existing proposal
API family. When Slice 5 or a later API-bearing slice adds models, it must update:

1. OpenAPI examples and field descriptions,
2. API vocabulary inventory,
3. no-alias contract coverage,
4. proposal lifecycle/replay contract tests,
5. docs and wiki supported-feature posture.

The preferred semantic vocabulary is `proposal_narrative`, not `ai_text`, `generated_text`,
`commentary_blob`, or `client_ready_commentary`.

## No Public API v2 Required

Current proposal lifecycle, artifact, workspace, replay, and support routes already expose stable
resource families under `/advisory/proposals/*` and `/advisory/workspaces/*`. Proposal narrative can
be added as a subresource under `/advisory/proposals/{proposal_id}` without changing existing
contracts or introducing `/v2`.

Compatibility rule:

1. existing simulation, artifact, lifecycle, workspace, and replay responses remain backward
   compatible,
2. narrative fields are additive and opt-in,
3. unsupported client-ready requests fail closed with structured reason codes,
4. Gateway and Workbench consume canonical Advise narrative endpoints only when those endpoints are
   implemented and advertised through supportability/capabilities.

## First Implementation Scope

The first implementation-bearing slice should build only deterministic advisor-review narrative:

1. source: persisted proposal version detail and evidence bundle,
2. audience: `ADVISOR_REVIEW`,
3. generation mode: `DETERMINISTIC_TEMPLATE`,
4. sections: `EXECUTIVE_SUMMARY`, `RECOMMENDATION_RATIONALE`,
   `RISK_AND_CONCENTRATION`, `MATERIAL_CHANGES`, `ALTERNATIVES_CONSIDERED`,
   `APPROVALS_AND_NEXT_STEPS`, and `LIMITATIONS_AND_DISCLOSURES`,
5. status: one of `READY_FOR_ADVISOR_REVIEW`, `BLOCKED_BY_MISSING_EVIDENCE`,
   or `DEGRADED_SOURCE_LIMITED`,
6. review state: `AWAITING_ADVISOR_REVIEW`,
7. no client-ready output,
8. no report/render/archive handoff,
9. no Gateway or Workbench claim,
10. no AI-assisted output unless a later slice adds the explicit `lotus-ai` workflow-pack boundary.

## Implementation Blockers Before Slice 5

Slice 5 must not start until Slice 4 settles whether proposal narrative becomes a governed data
product and how supportability/capability posture is represented.

Still blocked:

1. persisted narrative version schema and exact replay requirements,
2. review-action audit model,
3. policy/disclosure blockers for client-draft and client-ready audiences,
4. AI workflow-pack contract for proposal narrative,
5. `/platform/capabilities` promotion rule,
6. report/render/archive, Gateway, Workbench, and `lotus-manage` consumption proof.

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Assessment document exists | This file maps artifact, proposal detail, workspace, lifecycle, replay, decision summary, alternatives, and UI needs with code/test evidence. |
| Narrative contract reconciled | Contract baseline is additive, snake_case, proposal-family scoped, and explicitly defers OpenAPI/API vocabulary changes until API-bearing implementation. |
| First implementation explicit | First implementation scope is deterministic `ADVISOR_REVIEW` narrative only. |
| No implementation begins | No source route, model, persistence, capability, or OpenAPI contract is added in this slice. |

## README And Wiki Decision

README/wiki source changes are required because Slice 3 changes RFC closure truth and sets the
implementation boundary for future demo-facing narrative work.

Supported Features must remain non-claiming: generated proposal narrative remains planned until a
later implementation-bearing slice passes local gates, PR gates, main releasability, and wiki
publication.

## Next Slice

RFC-0023 may proceed to Slice 4 data-product and supportability baseline after Slice 3 is merged,
CI is green, wiki publication is complete, and branch hygiene is clean.
