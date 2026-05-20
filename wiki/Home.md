# Lotus Advise Wiki

`lotus-advise` is the Lotus advisory workflow service. It owns advisor-led proposal simulation orchestration, proposal lifecycle state, approvals and consent workflow behavior, advisory workspace drafting, execution readiness posture, and bounded tactical house-view affected-cohort evaluation.

It does not own canonical portfolio source data, risk methodology, performance methodology, or downstream execution. Those responsibilities stay with upstream or adjacent Lotus services and are consumed through governed seams.

## Start Here

- [Overview](Overview)
- [Getting Started](Getting-Started)
- [Architecture](Architecture)
- [API Surface](API-Surface)
- [Supported Features](Supported-Features)
- [Proposal Lifecycle](Proposal-Lifecycle)
- [Advisory Workspace](Advisory-Workspace)
- [Development Workflow](Development-Workflow)
- [Operations Runbook](Operations-Runbook)
- [Security and Governance](Security-and-Governance)
- [Troubleshooting](Troubleshooting)
- [Integrations](Integrations)
- [Validation and CI](Validation-and-CI)
- [RFC Index](RFC-Index)

## Service Identity

- Service: `lotus-advise`
- API docs: `/docs`
- Health probes:
  - `/health`
  - `/health/live`
  - `/health/ready`

## What This Service Owns

- advisory proposal simulation orchestration
- deterministic proposal artifact generation
- persisted proposal lifecycle state and immutable versioning
- approval and consent capture
- delivery, reporting-request, and execution-handoff posture
- workspace drafting, save/resume/compare, and lifecycle handoff
- backend-owned proposal decision summary and proposal alternatives surfaces
- source-owned tactical house-view affected cohorts for supplied source-backed candidates

## What This Service Does Not Own

- portfolio, holdings, cash, prices, FX, and instrument source authority
- risk methodology and concentration analytics authority
- performance analytics authority
- report rendering ownership
- execution ownership
- discretionary portfolio-management campaigns or trade approval

## Grounding Sources

- repo README
- `docs/architecture/RFC-0082-upstream-contract-family-map.md`
- `docs/demo/README.md`
- `docs/operations/development-workflow-and-ci-strategy.md`
- `docs/rfcs/README.md`
- FastAPI route families under `src/api/`
