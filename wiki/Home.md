# Lotus Advise Wiki

`lotus-advise` is the Lotus advisory workflow service. It owns advisor-led proposal simulation orchestration, proposal lifecycle state, approvals and consent workflow behavior, advisory workspace drafting, and execution readiness posture.

It does not own canonical portfolio source data, risk methodology, performance methodology, or downstream execution. Those responsibilities stay with upstream or adjacent Lotus services and are consumed through governed seams.

## Start Here

- [Overview](Overview)
- [Getting Started](Getting-Started)
- [Architecture](Architecture)
- [API Surface](API-Surface)
- [Proposal Lifecycle](Proposal-Lifecycle)
- [Advisory Workspace](Advisory-Workspace)
- [Integrations](Integrations)
- [Validation and CI](Validation-and-CI)
- [RFC Map](RFC-Map)

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

## What This Service Does Not Own

- portfolio, holdings, cash, prices, FX, and instrument source authority
- risk methodology and concentration analytics authority
- performance analytics authority
- report rendering ownership
- execution ownership

## Grounding Sources

- repo README
- `docs/architecture/RFC-0082-upstream-contract-family-map.md`
- `docs/demo/README.md`
- `docs/operations/development-workflow-and-ci-strategy.md`
- `docs/rfcs/README.md`
- FastAPI route families under `src/api/`
