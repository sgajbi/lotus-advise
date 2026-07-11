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
- unavailable risk authority always carries degraded evidence; dependency-state failures use
  `LOTUS_RISK_DEPENDENCY_UNAVAILABLE`, while configured enrichment failures use
  `LOTUS_RISK_ENRICHMENT_UNAVAILABLE`

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

## `lotus-idea`

Current governed usage includes:

- downstream consumption of Advise data-product posture as opportunity-intelligence evidence
- source-safe proposal-intake route foundation through `POST /advisory/proposals/idea-intake`

Boundary rule:

- `lotus-idea` owns idea candidates and conversion-intent evidence
- `lotus-advise` owns advisory proposal lifecycle, suitability, approval, and client-publication
  authority
- the current route proves only route existence and remains `not_certified`; it does not persist
  proposal records, create orders, certify data-product realization, or promote a supported feature

## `lotus-report`

Current usage:

- report-request integration boundary for Lotus-branded advisory outputs

Boundary rule:

- report ownership stays outside `lotus-advise`
- report submissions require bounded trusted tenant and actor identity; unsafe or absent identity
  fails closed before HTTP submission
- report submissions require source-derived as-of date, reporting currency, and jurisdiction; the
  mapper does not manufacture current-date, USD, or SG fallbacks
- memo and policy sign-off report packages use bounded status retrieval before projecting
  readiness. `ARCHIVED` is returned only from terminal report-owned archive evidence; accepted,
  running, missing-status, malformed-status, and status-lookup failures stay explicit pending or
  unavailable postures with the report job id preserved for recovery.

## `lotus-ai`

Current implemented usage:

- workspace-rationale integration boundary
- proposal narrative, proposal memo, policy-evidence, advisory-copilot, and workspace-rationale
  workflow-pack calls use the same trusted tenant envelope

Boundary rule:

- AI may assist with grounded rationale generation
- AI must not become the authority for suitability, approvals, trade generation, or proposal alternatives
- AI workflow-pack calls require `LOTUS_ADVISE_TENANT_ID`; unsafe or absent tenant identity fails
  closed before HTTP submission
