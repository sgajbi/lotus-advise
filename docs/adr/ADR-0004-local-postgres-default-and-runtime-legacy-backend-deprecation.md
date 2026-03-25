# ADR-0004: Advisory Postgres Runtime Default and Legacy Backend Removal Direction

## Status

Accepted

## Context

Advisory runtime is converging on PostgreSQL-only service behavior.
For a codebase prioritizing environment parity and bank-grade operability, active runtime should
match that posture in every environment.

The codebase still contains test-time and historical references to legacy runtime backends
(`IN_MEMORY`, `SQL/SQLITE`, `ENV_JSON`), but they should no longer be described as active service
runtime choices.

## Decision

1. Make advisory Postgres runtime the active runtime default everywhere.
2. Keep legacy repository adapters, if needed, only for narrow test and transition scenarios.
3. Remove documentation and runtime language that imply mixed backend support for active service
   startup.

## Consequences

Positive:

- Better environment parity by default.
- Lower risk of “works locally, fails in production” persistence mismatches.
- Clearer operational story for advisory runtime ownership and supportability.

Trade-offs:

- Local runtime now requires Postgres availability.
- Test-only in-memory adapters remain clearly separated from active service runtime.

## Follow-up

- Complete the remaining runtime cleanup under `RFC-0005`.

