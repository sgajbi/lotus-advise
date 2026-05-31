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
- `LOTUS_RISK_TIMEOUT_SECONDS`
- `LOTUS_RISK_RETRY_ATTEMPTS`
- `LOTUS_RISK_RETRY_BACKOFF_SECONDS`

Operational behavior:

- transient `5xx`, `429`, and network failures are retried with bounded attempts
- `4xx` contract or request failures are not retried
- retry attempts default to `2` and are capped at `5`
- retry backoff defaults to `0.1` seconds and is capped at `2.0` seconds

## `lotus-performance`

Current posture:

- readiness dependency only
- not a current advisory source-data input

If advisory behavior later depends on performance analytics, that dependency should be classified explicitly instead of being inferred through another service.

## `lotus-manage`

Current governed usage includes:

- downstream consumption of `TacticalHouseViewAffectedCohort:v1`

Boundary rule:

- `lotus-advise` evaluates affected-cohort membership for supplied source-backed candidates
- `lotus-manage` owns discretionary portfolio-management campaigns, policies, rebalance workflows,
  and execution evidence

## `lotus-report`

Current usage:

- report-request integration boundary for Lotus-branded advisory outputs

Boundary rule:

- report ownership stays outside `lotus-advise`

## `lotus-ai`

Current implemented usage:

- workspace-rationale integration boundary

Boundary rule:

- AI may assist with grounded rationale generation
- AI must not become the authority for suitability, approvals, trade generation, or proposal alternatives
