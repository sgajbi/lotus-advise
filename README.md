# lotus-advise

Advisor-led proposal simulation and lifecycle service for the Lotus ecosystem.

Repository-local engineering context: [REPOSITORY-ENGINEERING-CONTEXT.md](REPOSITORY-ENGINEERING-CONTEXT.md)

RFC-0082 upstream contract-family map:
[docs/architecture/RFC-0082-upstream-contract-family-map.md](docs/architecture/RFC-0082-upstream-contract-family-map.md)

## Purpose And Scope

`lotus-advise` owns advisory-only workflows:

- advisor-led proposal simulation
- proposal lifecycle state and approvals
- consent and execution-readiness workflow behavior
- advisory workspace drafting and handoff
- proposal decision-summary and proposal-alternatives persistence across simulation, artifact,
  replay, workspace, and operator evidence surfaces

It does not own discretionary portfolio-management operations. Those belong to `lotus-manage`.

## Ownership And Boundaries

`lotus-advise` is the advisory workflow authority, but it is not the data or analytics authority for
the underlying portfolio ecosystem.

It depends on:

- `lotus-core`
  canonical portfolio state, stateful advisory context, and advisory simulation execution authority
- `lotus-risk`
  concentration and risk-lens enrichment authority
- `lotus-performance`
  readiness dependency only in the current posture, not an advisory source-data dependency

It is consumed primarily through `lotus-gateway` for integrated product flows.

## Current Operational Posture

1. `lotus-advise` is advisory-only after the split from `lotus-manage`.
2. Runtime smoke and production-profile guardrail validation are part of the real merge contract.
3. Proposal simulation, artifact, workspace, replay, and lifecycle surfaces expose persisted
   backend-owned `proposal_decision_summary` and `proposal_alternatives`.
4. Canonical upstream integration with `lotus-core` and `lotus-risk` matters for truthful proposal behavior.

## Architecture At A Glance

Main runtime surfaces come from [src/api/main.py](src/api/main.py):

- advisory simulation
  `/advisory/proposals/simulate`, `/advisory/proposals/artifact`
- advisory proposal lifecycle
  persisted proposal lifecycle, async, support, delivery, and execution handoff surfaces
- advisory workspace
  workspace drafting, evaluate/save/resume/compare, assistant rationale, and lifecycle handoff
- integration
  platform capability and readiness contract publication
- platform surfaces
  `/health`, `/health/live`, `/health/ready`, `/docs`

Key code areas:

- `src/api/`
  FastAPI entrypoints, routers, runtime readiness, observability, and OpenAPI enrichment
- `src/core/advisory/`
  advisory-specific orchestration, decision summary, alternatives, suitability, and artifact logic
- `src/core/proposals/`
  proposal lifecycle models, services, and repository abstractions
- `src/core/workspace/`
  workspace contracts and drafting/evaluation models
- `src/integrations/`
  Lotus Core, Risk, AI, and Report integration seams
- `docs/`
  architecture, standards, RFCs, project overview, and workflow documentation

## Quick Start

Install dependencies:

```bash
make install
```

Run the service locally:

```bash
make run
```

API docs endpoint: `/docs`

Local validation commands:

- `make check`
  fast local quality gate
- `make ci`
  full local PR-grade gate with project-scoped dependency health, coverage, Docker build,
  Postgres runtime smoke, and production-profile guardrail validation
- `make ci-local-docker`
  Linux container parity for the host-side CI contract

## Validation And CI Lanes

`lotus-advise` follows the Lotus multi-lane model:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

Repo-native gate mapping:

- `make check`
  lint, typecheck, OpenAPI gate, no-alias gate, vocabulary gate, and unit tests
- `make ci`
  dependency health, governance gates, migration smoke, security audit, combined coverage, Docker
  build, Postgres runtime smoke, and production-profile guardrail negatives
- `make ci-local`
  feature-lane style local proof without Docker parity

When the README changes, also run:

```bash
python -m pytest tests/unit/test_local_docker_runtime_contract.py -q
```

That test protects the canonical local Docker upstream URL documentation.

## Integration Boundaries

Local Docker runtime expects canonical upstream integrations to be explicit:

- `LOTUS_CORE_BASE_URL` should point at the lotus-core control-plane endpoint, for example `http://core-control.dev.lotus`
- `LOTUS_CORE_QUERY_BASE_URL` should point at the lotus-core query endpoint, for example `http://core-query.dev.lotus`
- `LOTUS_RISK_BASE_URL` should point at the lotus-risk API endpoint, for example `http://risk.dev.lotus`

This keeps proposal simulation and proposal risk-lens behavior aligned with the canonical service
authorities during local Docker validation.

Boundary rules that matter operationally:

1. proposal simulation must remain aligned with authoritative upstream data and risk posture
2. decision-summary, proposal-alternatives generation, ranking, selection, approval-requirement,
   and material-change semantics are backend-owned contracts
3. UI and support layers must not regenerate, rerank, or re-infer proposal decision semantics
4. REST/OpenAPI remains the canonical integration contract; gRPC is not justified for current advisory upstream calls

## Operations And Runtime Posture

Runtime behavior is not just unit-logic-only here:

- startup validates proposal repository boot readiness and advisory runtime persistence
- readiness fails closed when required persistence or runtime seams are unavailable
- CI includes real runtime smoke and production-profile guardrail checks
- advisory lifecycle and operator evidence depend on persisted workflow state staying truthful

Key references:

- [docs/documentation/project-overview.md](docs/documentation/project-overview.md)
- [docs/architecture/RFC-0082-upstream-contract-family-map.md](docs/architecture/RFC-0082-upstream-contract-family-map.md)
- [docs/standards/](docs/standards)
- [docs/rfcs/README.md](docs/rfcs/README.md)

## Documentation Map

- project overview:
  [docs/documentation/project-overview.md](docs/documentation/project-overview.md)
- RFC index:
  [docs/rfcs/README.md](docs/rfcs/README.md)
- upstream contract-family map:
  [docs/architecture/RFC-0082-upstream-contract-family-map.md](docs/architecture/RFC-0082-upstream-contract-family-map.md)
- local standards:
  [docs/standards](docs/standards)

## Wiki Source

Repository-authored wiki pages live under [wiki/](wiki). If the GitHub wiki is published later,
keep `wiki/` as the canonical source and treat any separate `*.wiki.git` clone as publication
plumbing only.
