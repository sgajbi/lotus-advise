# Overview

`lotus-advise` is the advisory workflow service in the Lotus ecosystem. It turns portfolio intent into a governed advisory proposal flow by combining:

1. canonical source-data and simulation authority from `lotus-core`,
2. risk-lens enrichment from `lotus-risk`,
3. advisory-owned workflow state, approvals, and evidence continuity,
4. optional supporting seams such as workspace rationale through `lotus-ai` and report requests through `lotus-report`.

## Primary Responsibilities

- simulate advisory proposals from normalized `stateless` and `stateful` inputs
- build deterministic proposal artifacts
- persist advisory proposals with immutable versions
- manage lifecycle transitions, approvals, and consent
- expose support and delivery posture from append-only workflow history
- provide an advisory workspace for iterative draft construction before lifecycle handoff
- evaluate tactical house-view affected cohorts from bank-authored instructions and source-backed
  candidate portfolios

## Repository Posture

The repository is advisory-only. It is intentionally separated from discretionary portfolio management and should not absorb `lotus-manage` responsibilities.

The current implementation also makes these backend-owned surfaces explicit:

- `proposal_decision_summary`
- `proposal_alternatives`
- `TacticalHouseViewAffectedCohort:v1`

Those outputs are generated and ranked inside `lotus-advise`. UI or support layers should display them, not recreate or reinterpret them as a separate authority.

## Bounded Domain

`lotus-advise` may evaluate:

- proposal readiness
- suitability posture
- approval requirements
- lifecycle progression
- advisor workflow continuity
- tactical house-view affected-cohort membership for supplied candidate sets

It must not become the source of truth for:

- portfolio valuation
- performance attribution
- risk methodology
- benchmark methodology
- execution settlement truth
- discretionary portfolio-management campaigns or trade approval

## Runtime Shape

At application startup the service validates:

- runtime persistence configuration
- proposal workflow repository readiness
- async operation recovery posture

The service also exposes health and readiness probes and enriches OpenAPI output for platform governance.
