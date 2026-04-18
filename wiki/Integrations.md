# Integrations

## Upstream dependencies

`lotus-advise` consumes:

- `lotus-core`
  canonical portfolio state and advisory simulation authority
- `lotus-risk`
  risk-lens enrichment authority
- `lotus-ai`
  governed advisor-assistive rationale support
- `lotus-report`
  report request integration seam

`lotus-performance` is currently a readiness dependency only and not an advisory source-data input.

## Boundary rules

1. do not duplicate core simulation semantics locally
2. do not duplicate risk methodology locally
3. fallback behavior must remain bounded and supportability-oriented, not pseudo-authoritative
4. REST/OpenAPI is the canonical current integration contract

## Canonical local upstream URLs

- `http://core-control.dev.lotus`
- `http://core-query.dev.lotus`
- `http://risk.dev.lotus`

## Deep reference

- [docs/architecture/RFC-0082-upstream-contract-family-map.md](../docs/architecture/RFC-0082-upstream-contract-family-map.md)
