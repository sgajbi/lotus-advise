# Architecture

## Runtime shape

`lotus-advise` is a FastAPI advisory service with four main surface families:

1. advisory simulation
2. proposal lifecycle
3. advisory workspace
4. integration and health surfaces

## Code layout

- `src/api/`
  FastAPI application, routers, readiness checks, observability, and OpenAPI enrichment
- `src/core/advisory/`
  advisory orchestration, alternatives, decision summary, artifact, and policy modules
- `src/core/proposals/`
  lifecycle models, services, and persistence abstractions
- `src/core/workspace/`
  workspace drafting, evaluation, and handoff contracts
- `src/integrations/`
  Lotus Core, Risk, AI, and Report integration seams
- `docs/`
  architecture, RFCs, standards, and project docs

## Critical seams

- `lotus-core`
  stateful context and advisory simulation authority
- `lotus-risk`
  risk-lens enrichment authority
- proposal persistence
  proposal lifecycle-focused PostgreSQL boundary
- workspace handoff
  bridge from iterative drafting to persisted lifecycle ownership

## Deep references

- [docs/documentation/project-overview.md](../docs/documentation/project-overview.md)
- [docs/architecture/RFC-0082-upstream-contract-family-map.md](../docs/architecture/RFC-0082-upstream-contract-family-map.md)
