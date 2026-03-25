# Data Model Ownership

- Service: `lotus-advise`
- Ownership: advisory proposal workflow and execution-readiness domain schema.

## Owned Domains

- Advisory proposal workflow persistence model.
- Schema migration history (`schema_migrations`) for advisory namespaces.

## Service Boundaries

- Core portfolio ledger, valuation, and transaction source data remains lotus-core-owned.
- Risk analytics remain lotus-risk-owned and consumed through APIs where needed.
- Performance analytics remain lotus-performance-owned and consumed through APIs where needed.
- Reporting payload generation remains lotus-report-owned.

## Schema Rules

- Advisory runtime data uses advisory-owned namespaces and tables only.
- No cross-service shared database access.

