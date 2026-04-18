# lotus-advise

Advisor-led proposal simulation, advisory workspace, and persisted proposal lifecycle service for Lotus.

Repository-local engineering context:
[REPOSITORY-ENGINEERING-CONTEXT.md](REPOSITORY-ENGINEERING-CONTEXT.md)

Upstream contract-family map:
[docs/architecture/RFC-0082-upstream-contract-family-map.md](docs/architecture/RFC-0082-upstream-contract-family-map.md)

## Purpose And Scope

`lotus-advise` owns advisory-only workflow behavior in the Lotus ecosystem.

It is responsible for:

- advisory proposal simulation orchestration
- deterministic proposal artifact generation
- advisory workspace drafting and handoff
- persisted proposal lifecycle state and immutable versioning
- approvals, consent, and execution-readiness posture
- backend-owned `proposal_decision_summary` and `proposal_alternatives`

It does not own discretionary management workflows, portfolio source data, risk methodology,
performance methodology, reporting ownership, or downstream execution ownership.

## Ownership And Boundaries

`lotus-advise` sits between product consumers and authoritative upstream services.

It depends on:

- `lotus-core`
  canonical portfolio context, source-data reads, and advisory simulation authority
- `lotus-risk`
  risk-lens enrichment and concentration authority
- `lotus-report`
  report-request seam
- `lotus-ai`
  workspace rationale seam
- `lotus-gateway`
  primary integrated product-facing consumer

Boundary rules that matter:

1. advisory-only workflows belong here; management workflows belong in `lotus-manage`
2. proposal alternatives and decision-summary semantics are backend-owned surfaces, not UI-derived interpretations
3. proposal simulation and alternatives must stay anchored to canonical upstream authorities
4. REST/OpenAPI remains the governed integration contract for current upstream calls

## Current Operational Posture

1. `lotus-advise` is scoped to advisory-only workflows after the split from `lotus-manage`.
2. Proposal simulation, artifact, workspace, replay, and lifecycle flows now expose persisted
   backend-owned `proposal_decision_summary` and `proposal_alternatives`.
3. Runtime smoke and production-profile guardrail validation are part of the actual CI contract.
4. Live operator evidence covers canonical and degraded decision-summary and alternatives posture.

## Architecture At A Glance

Main runtime surfaces come from [src/api/main.py](src/api/main.py):

- advisory simulation
  `POST /advisory/proposals/simulate`
  `POST /advisory/proposals/artifact`
- advisory proposal lifecycle
  create, version, transition, approval, delivery, execution, async, and support routes under
  `/advisory/proposals/*`
- advisory workspace
  iterative draft, save, resume, compare, rationale, and lifecycle handoff under
  `/advisory/workspaces/*`
- integration capabilities
  `GET /integration/capabilities`
- platform surfaces
  `/health`, `/health/live`, `/health/ready`, `/docs`

Key code areas:

- `src/api/`
  FastAPI app wiring, route families, and runtime support
- `src/core/advisory/`
  advisory artifact, funding, alternatives, decision summary, and policy logic
- `src/core/proposals/`
  persisted proposal lifecycle models and services
- `src/core/workspace/`
  advisory workspace contracts and state
- `src/integrations/`
  Lotus Core, Risk, AI, Report, and Performance seams
- `docs/`
  repo-local architecture, RFCs, demo payloads, and runbooks

## Repository Layout

- `src/api/`
  HTTP entrypoints and route families
- `src/core/`
  advisory domain, lifecycle, replay, and workspace logic
- `src/integrations/`
  upstream and adjacent service adapters
- `src/infrastructure/`
  Postgres migrations and proposal persistence implementations
- `docs/`
  repo-local architecture, RFCs, demo material, and runbooks
- `tests/`
  unit, integration, and e2e coverage
- `wiki/`
  canonical authored source for GitHub wiki publication

## Quick Start

Install dependencies:

```bash
make install
```

Run the service locally:

```bash
make run
```

Canonical local service identity for cross-app and demo-oriented flows:

- `http://advise.dev.lotus`

Quick probes:

```bash
curl http://advise.dev.lotus/health
curl http://advise.dev.lotus/health/ready
```

OpenAPI UI:

- `/docs`

Important local Docker runtime bindings:

- `LOTUS_CORE_BASE_URL`
- `LOTUS_CORE_QUERY_BASE_URL`
- `LOTUS_RISK_BASE_URL`

Canonical local Docker upstream defaults:

- `LOTUS_CORE_BASE_URL=http://core-control.dev.lotus`
- `LOTUS_CORE_QUERY_BASE_URL=http://core-query.dev.lotus`
- `LOTUS_RISK_BASE_URL=http://risk.dev.lotus`

## Common Commands

- `make install`
  install dependencies
- `make check`
  fast local quality gate
- `make ci`
  PR-grade local proof with dependency health, coverage, Docker build, Postgres runtime smoke, and
  production-profile guardrail validation
- `make ci-local`
  local feature-lane proof
- `make ci-local-docker`
  Linux container parity for the host-side CI contract
- `make run`
  local runtime

## Validation And CI Lanes

`lotus-advise` follows the Lotus multi-lane model:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

Repo-native gate mapping:

- `make check`
  fast local quality gate
- `make ci`
  PR-grade validation with dependency health, OpenAPI, vocabulary, no-alias governance, migration
  smoke, coverage, Docker build, Postgres runtime smoke, and production-profile guardrail checks
- `make ci-local`
  local feature-lane proof
- `make ci-local-docker`
  container parity

## API Contract Notes

Important public route groups:

1. advisory simulation and artifact
2. persisted proposal lifecycle
3. advisory operations and support
4. advisory workspace
5. integration capabilities

Contract rules that are easy to get wrong:

1. proposal simulation and artifact flows require `Idempotency-Key`
2. lifecycle persistence is immutable-by-version
3. support and delivery posture derive from append-only workflow history
4. workspace rationale is the implemented AI seam today; broader proposal narrative remains future work

## Integration Boundaries

- primary downstream consumer:
  `lotus-gateway`
- key upstreams:
  `lotus-core`, `lotus-risk`
- bounded adjacent seams:
  `lotus-report`, `lotus-ai`

Contract rule:

`lotus-advise` may orchestrate, persist, and shape advisory workflow evidence, but it must not
become the authority for source portfolio data, risk methodology, performance analytics, report
generation, or downstream execution truth.

## Operations And Runtime Posture

- use `advise.dev.lotus` for canonical local cross-app validation
- use readiness to confirm persistence and runtime boot posture before treating the service as healthy
- treat upstream simulation and risk failures as dependency issues first, not as reasons to invent local fallback truth
- keep proposal decision-summary and alternatives behavior aligned to canonical and degraded live evidence

## Documentation Map

- architecture and business overview:
  [docs/documentation/project-overview.md](docs/documentation/project-overview.md)
- upstream contract-family map:
  [docs/architecture/RFC-0082-upstream-contract-family-map.md](docs/architecture/RFC-0082-upstream-contract-family-map.md)
- demo scenarios:
  [docs/demo/README.md](docs/demo/README.md)
- development workflow:
  [docs/operations/development-workflow-and-ci-strategy.md](docs/operations/development-workflow-and-ci-strategy.md)
- Postgres rollout runbook:
  [docs/documentation/postgres-migration-rollout-runbook.md](docs/documentation/postgres-migration-rollout-runbook.md)
- RFC index:
  [docs/rfcs/README.md](docs/rfcs/README.md)

## Wiki Source

Repository-authored wiki pages live under [wiki/](wiki). Keep `wiki/` as the canonical authored
source and treat any separate `*.wiki.git` clone as publication plumbing only.
