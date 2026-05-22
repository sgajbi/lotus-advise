# Supported Features

This page separates implementation-backed `lotus-advise` capability from roadmap intent. It is
written for business, engineering, operations, sales, pre-sales, and demo preparation.

## Current Functional Capability Matrix

| Capability | Current support | Primary API or source | Boundary |
| --- | --- | --- | --- |
| Advisory proposal simulation | Supported | `POST /advisory/proposals/simulate` | Simulation execution stays anchored to `lotus-core` authority. |
| Proposal artifact generation | Supported | `POST /advisory/proposals/artifact` | Artifact generation is deterministic advisory evidence, not report rendering ownership. |
| Persisted proposal lifecycle | Supported | `/advisory/proposals/*` | Versions are immutable and workflow history is append-only. |
| Approval and consent workflow | Supported | `/advisory/proposals/{proposal_id}/approvals` and transitions | Approval posture is advisory workflow evidence, not downstream trade approval. |
| Delivery, report-request, and execution-handoff posture | Supported | delivery, report-request, execution-handoff, and execution-status routes | Execution handoff/status payloads carry ownership-boundary evidence; execution truth remains outside `lotus-advise`. |
| Advisory workspace drafting | Supported | `/advisory/workspaces/*` | Workspace state is pre-lifecycle advisory drafting, with explicit handoff into proposal ownership. |
| Workspace AI rationale | Supported through governed seam | `/advisory/workspaces/{workspace_id}/assistant/rationale` | Uses the bounded `lotus-ai` workspace rationale seam; broad proposal narrative remains RFC-0023 future work. |
| Proposal decision summary | Supported | simulation, artifact, workspace, replay, and lifecycle surfaces | Backend-owned decision summary; UI and support layers must not infer it independently. |
| Proposal alternatives | Supported | simulation, artifact, workspace, replay, and lifecycle surfaces | Alternatives remain anchored to canonical simulation and risk enrichment. |
| Tactical house-view affected cohorts | Supported | `POST /advisory/tactical-house-view/cohorts/evaluate` | Evaluates supplied source-backed candidate portfolios only; no global portfolio discovery or DPM campaign ownership. |
| Integration capability discovery | Supported | `GET /platform/capabilities` | Publishes feature, workflow, dependency-readiness evidence, and supportability posture for Gateway and platform consumers. |

## Current Non-Functional Capability Matrix

| Capability | Current support | Evidence |
| --- | --- | --- |
| OpenAPI and Swagger quality | Supported | `make openapi-gate` plus contract documentation tests. |
| API vocabulary and no-alias governance | Supported | `make api-vocabulary-gate` and `make no-alias-gate`. |
| Domain-product declarations | Supported | `contracts/domain-data-products/` and `make domain-data-products-gate`. |
| Trust telemetry fixture validation | Supported | `contracts/trust-telemetry/` and `tests/unit/test_trust_telemetry.py`. |
| Runtime smoke and production guardrails | Supported | `make ci` includes Postgres runtime smoke and production-profile guardrail negatives. |
| Dependency health and security audit | Supported | `make verify-dependencies` and `make security-audit`. |
| Supportability metrics and readiness evidence | Supported | `GET /platform/capabilities` documents bounded labels for `lotus_advise_advisory_supportability_total` and bounded dependency readiness basis fields. |
| Live cross-service evidence | Supported when the local stack is configured | Live validation scripts prove canonical and degraded proposal behavior. |

## Active Roadmap RFCs

These items are documented as future work and must not be presented as currently supported until
their implementation, tests, live proof, README/wiki updates, and `/platform/capabilities` posture
are complete.

| RFC | Feature | Product value | Current support |
| --- | --- | --- | --- |
| `RFC-0023` | Grounded advisory AI narrative and client-ready proposal commentary | Creates governed advisor-review, compliance-review, and client-ready proposal narrative from deterministic evidence. | Slices 0-1 complete for source authority and platform-scaffolding review; generated proposal narrative remains planned |
| `RFC-0024` | Advisor proposal memo and evidence pack | Turns proposal evidence into an advisor, compliance, operations, audit, and sales-ready memo package. | Planned RFC only |
| `RFC-0025` | Enterprise suitability and best-interest policy packs | Adds versioned policy packs for suitability, best-interest, product eligibility, disclosures, approvals, and source-readiness gaps. | Planned RFC only |
| `RFC-0026` | Advisor cockpit operating workflow | Creates backend-owned advisor worklists, action items, meeting-preparation packets, and workflow readiness summaries. | Planned RFC only |
| `RFC-0027` | Governed advisory AI copilot | Adds bounded AI workflow-pack actions for proposal explanation, evidence Q&A, preparation, and review support. | Planned RFC only |
| `RFC-0028` | Bank demo journey and client-ready proof | Creates repeatable, implementation-backed advisory demo proof with supported-claim governance. | Planned RFC only |

## Advisory Flow

```mermaid
flowchart LR
    Advisor[Advisor or Gateway consumer] --> Advise[lotus-advise]
    Advise --> Core[lotus-core source data and simulation]
    Advise --> Risk[lotus-risk concentration lens]
    Advise --> AI[lotus-ai workspace rationale]
    Advise --> Report[lotus-report report request seam]
    Advise --> Gateway[lotus-gateway]
    Gateway --> Workbench[lotus-workbench]
```

## RFC-0023 Narrative Implementation Boundary

```mermaid
flowchart LR
    Core[lotus-core source facts] --> Grounding[Future RFC-0023 grounding packet]
    Risk[lotus-risk risk lens] --> Grounding
    Decision[lotus-advise decision summary] --> Grounding
    Alternatives[lotus-advise alternatives] --> Grounding
    Grounding --> Narrative[Future proposal narrative authority]
    AI[lotus-ai workflow-pack execution] --> Narrative
    Narrative --> Review[Human review and replay gates]
    Review --> Gateway[Future Gateway consumption]
    Gateway --> Workbench[Future Workbench rendering]
    Review --> Report[Future report/render/archive handoff]
```

The diagram is deliberately future-facing. Today, only the source-map and ownership gate is
implementation-backed for RFC-0023; generated proposal narrative, client-ready commentary, and
document artifact inclusion remain planned until the implementing slices close.

## Integration Boundaries

```mermaid
flowchart TB
    Core[lotus-core<br/>portfolio, holdings, cash, prices, FX, simulation authority]
    Risk[lotus-risk<br/>risk methodology and concentration]
    Advise[lotus-advise<br/>advisor-led proposal workflow]
    Gateway[lotus-gateway<br/>product-facing composition]
    Manage[lotus-manage<br/>DPM campaigns and operations]
    AI[lotus-ai<br/>workspace rationale seam]
    Report[lotus-report<br/>report generation seam]

    Core --> Advise
    Risk --> Advise
    AI --> Advise
    Report --> Advise
    Advise --> Gateway
    Advise --> Manage
```

## Demo And Pitch Boundaries

- Safe to claim: advisor-led proposal simulation, lifecycle evidence, approval and consent posture,
  workspace drafting, decision summaries, proposal alternatives, supportability metrics, and
  governed tactical house-view affected cohorts are implementation-backed.
- Do not claim: `lotus-advise` owns portfolio books, risk methodology, performance methodology,
  report rendering, OMS execution, discretionary campaign workflows, or global portfolio-universe
  discovery.
- For client demos, prepare with `GET /platform/capabilities`, `/health/ready`, and the relevant
  proposal or workspace routes so readiness claims match the current runtime posture.
- When a dependency is degraded, use the capability contract's `readiness_basis` and
  `degraded_reason` fields to explain whether the issue is missing configuration, a failed runtime
  probe, or a configuration-only non-production posture.
- When explaining execution posture, use the `execution_ownership` evidence to distinguish
  advisory handoff/status reconciliation from downstream execution system-of-record truth.
