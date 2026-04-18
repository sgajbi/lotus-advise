# Architecture

## Service Role

`lotus-advise` sits between authoritative upstream portfolio/risk data and advisory workflow consumers. Its job is to convert canonical portfolio context into governed advisory decisions, proposal versions, and workflow evidence.

## Main Runtime Areas

### API Layer

FastAPI route families are organized into:

- advisory simulation
- advisory proposal lifecycle
- advisory operations and support
- advisory workspace
- integration
- health and monitoring

### Advisory Domain

The core advisory domain includes:

- proposal orchestration
- funding logic
- suitability and gate evaluation
- decision summary generation
- artifact generation
- proposal alternatives normalization, enrichment, projection, and ranking

### Lifecycle Domain

The persisted lifecycle model includes:

- proposal records
- immutable proposal versions
- workflow events
- approval records
- async operation tracking
- idempotency tracking

The repository supports both in-memory and PostgreSQL-backed proposal persistence, but the active runtime direction is PostgreSQL-backed persistence with migration support.

### Workspace Domain

The workspace surface exists for iterative drafting before formal proposal lifecycle ownership begins. It supports:

- session creation
- draft actions
- deterministic re-evaluation
- save and resume
- compare to saved version
- replay evidence lookup
- lifecycle handoff into persisted proposal ownership

## Boundary Rules

### `lotus-core`

`lotus-core` remains the authority for:

- portfolio source data
- holdings and cash reads
- instrument, price, and FX reads
- advisory simulation execution contract

`lotus-advise` must not duplicate `lotus-core` execution semantics or source-data authority locally.

### `lotus-risk`

`lotus-risk` remains the authority for risk-lens enrichment and concentration methodology.

### `lotus-performance`

`lotus-performance` is currently a readiness dependency, not a consumed analytics input contract for proposal behavior.

### `lotus-report`

Reporting can be requested through `lotus-advise`, but report generation ownership stays outside this service.

### `lotus-ai`

The current implemented AI seam is workspace rationale generation. Future proposal narrative capability is documented in RFC-0023 and is not yet the active implemented source of truth.
