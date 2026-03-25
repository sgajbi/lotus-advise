# ADR-0002: PostgreSQL as Target Persistence Backend for lotus-advise

## Status

Accepted

## Context

Advisory workflows require durable, auditable, and scalable persistence for production operations.
Current adapters (in-memory and SQLite) are useful for local development and incremental delivery
but are not the long-term production target.

## Decision

Set PostgreSQL as the target production persistence backend for advisory workflow storage:

- advisory proposal lifecycle storage
- advisory supportability and operational state storage

Keep in-memory (and optionally SQLite) adapters for local and test profiles behind backend configuration flags.

## Consequences

- Unified enterprise persistence strategy for advisory runtime workflows.
- Better concurrency, indexing, retention operations, and managed backup/HA capabilities.
- Requires migration tooling discipline and staged rollout by environment.

