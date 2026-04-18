# Integrations

## Current Upstream Posture

`lotus-advise` follows the upstream contract-family map documented in RFC-0082.

## `lotus-core`

Current governed usage includes:

- advisory simulation execution
- portfolio reads
- positions reads
- cash balance reads
- instrument reference reads
- price reads
- FX reads
- enrichment-bulk support
- classification taxonomy support

Environment bindings:

- `LOTUS_CORE_BASE_URL`
- `LOTUS_CORE_QUERY_BASE_URL`

Important rule:

- simulation execution authority lives on the control-plane binding
- query reads do not substitute for execution authority

## `lotus-risk`

Current governed usage includes:

- concentration and risk-lens enrichment for proposal alternatives and readiness posture

Environment binding:

- `LOTUS_RISK_BASE_URL`

## `lotus-performance`

Current posture:

- readiness dependency only
- not a current advisory source-data input

If advisory behavior later depends on performance analytics, that dependency should be classified explicitly instead of being inferred through another service.

## `lotus-report`

Current usage:

- report request seam for Lotus-branded advisory outputs

Boundary rule:

- report ownership stays outside `lotus-advise`

## `lotus-ai`

Current implemented usage:

- workspace rationale seam

Boundary rule:

- AI may assist with grounded rationale generation
- AI must not become the authority for suitability, approvals, trade generation, or proposal alternatives
