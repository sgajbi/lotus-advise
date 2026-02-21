# ADR-0011: Local Postgres Default and Legacy Runtime Backend Deprecation

## Status

Accepted

## Context

Production persistence is now enforced as Postgres-only under `APP_PERSISTENCE_PROFILE=PRODUCTION`.
For a solo-maintained codebase prioritizing environment parity, local runtime should match production
as closely as possible by default.

The codebase still contains legacy runtime backends (`IN_MEMORY`, `SQL/SQLITE`, `ENV_JSON`) that
remain useful for narrow unit-test scenarios and transition safety, but they should no longer be
the primary runtime path.

## Decision

1. Make Postgres-backed runtime the local default in containerized startup:
   - `docker-compose.yml` defaults use Postgres DSNs and Postgres backends.
2. Keep legacy runtime backends temporarily, but mark them deprecated at runtime:
   - `DPM_SUPPORTABILITY_STORE_BACKEND`: `IN_MEMORY` / `SQL` / `SQLITE`
   - `PROPOSAL_STORE_BACKEND`: `IN_MEMORY`
   - `DPM_POLICY_PACK_CATALOG_BACKEND`: `ENV_JSON`
3. Emit `DeprecationWarning` when legacy runtime backends are selected.

## Consequences

Positive:

- Better local-to-production parity by default.
- Lower risk of “works locally, fails in production” persistence mismatches.
- Migration path remains safe because legacy backends are still available during transition.

Trade-offs:

- Local runtime now requires Postgres availability by default.
- Contributors using legacy paths must explicitly accept deprecation warnings.

## Follow-up

- Plan final removal of legacy runtime backends in a dedicated RFC once remaining transition
  dependencies are cleared.
