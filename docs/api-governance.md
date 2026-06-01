# Lotus Advise API Governance

Lotus Advise API governance is enforced progressively through repo-native OpenAPI gates,
vocabulary checks, no-alias checks, and current report-only Spectral rules.

## Current Standards

- Endpoint documentation should include summaries, descriptions, tags, operation IDs, response
  models, request models where applicable, examples, and standard error responses.
- Private-banking vocabulary should remain business-facing and avoid unsupported client-ready,
  legal, regulatory, OMS, order, fill, or settlement claims.
- Supportability boundaries must be explicit when an endpoint exposes internal review, proposal,
  or advisory-copilot output.
- Mutating workflows should define idempotency behavior and audit/lineage posture.
- Correlation IDs should be accepted or propagated where API workflow tracing matters.

## Current Evidence

- `make openapi-gate`
- `make no-alias-gate`
- `make api-vocabulary-gate`
- `.spectral.yaml` for report-only API documentation rules
- `quality/api_governance_rules.md`

## Current Gaps

- Spectral execution is configured but not yet enforced in CI.
- RFC 7807/problem-details is a future migration unless a route family already implements it.
- Filtering, sorting, pagination, and deprecation rules still need full cross-endpoint inventory.
