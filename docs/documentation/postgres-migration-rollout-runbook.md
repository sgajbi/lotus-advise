# PostgreSQL Migration Rollout Runbook

## Scope

Runbook for forward-only schema migration rollout for:

- advisory proposals Postgres namespace (`proposals`)

## Preconditions

- PostgreSQL is reachable and healthy.
- Runtime DSNs are configured:
  - `PROPOSAL_POSTGRES_DSN`
- Application image/version to deploy is already tested in non-production.
- Production compose override available:
  - `docker-compose.production.yml`

## Runtime Contract

- Active `lotus-advise` runtime is PostgreSQL-only.
- Startup always enforces the advisory Postgres contract.
- Required backend settings:
  - `PROPOSAL_STORE_BACKEND=POSTGRES`
  - `PROPOSAL_POSTGRES_DSN` must be configured

## Migration Command

Use the shared migration tool before switching traffic:

```bash
python scripts/postgres_migrate.py --target all
```

Optional per-namespace commands:

```bash
python scripts/postgres_migrate.py --target proposals
```

Production contract check (profile/env/migration readiness):
Production contract check (runtime/env/migration readiness):

```bash
python scripts/production_cutover_check.py --check-migrations
```

## Startup Sequencing

1. Start/verify Postgres instance health.
2. Apply migrations (`scripts/postgres_migrate.py`).
3. Validate production contract (`scripts/production_cutover_check.py --check-migrations`).
4. Start API services with advisory Postgres runtime enabled:
   - `PROPOSAL_STORE_BACKEND=POSTGRES`
5. Run advisory smoke API checks.
6. Shift traffic.

Do not start app replicas with Postgres backend enabled before migrations have completed.

## Safety Controls

- Migrations are forward-only.
- Applied migration checksums are stored in `schema_migrations`.
- Migration execution is wrapped in a namespace-scoped PostgreSQL advisory lock
  to avoid concurrent deploy races.
- If a checked-in migration file is modified after apply, execution fails with:
  - `POSTGRES_MIGRATION_CHECKSUM_MISMATCH:{namespace}:{version}`
- Startup runtime guardrails fail-fast with explicit reason codes:
  - `PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES`
  - `PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN`

## CI Smoke Checks

CI executes:

1. `python scripts/postgres_migrate.py --target all`
2. Live Postgres integration tests:
   - `tests/integration/advisory/engine/test_engine_proposal_repository_postgres_integration.py`
3. Advisory Postgres startup smoke:
   - starts API with advisory Postgres backend.
4. Runtime guardrail negatives:
  - validates startup fails with:
    - `PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES`
    - `PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN`
5. Production cutover contract check:
   - `python scripts/production_cutover_check.py --check-migrations`
6. Optional nightly/manual deep validation:
   - `.github/workflows/nightly-postgres-full.yml`
   - runs integration repositories plus live API demo pack on advisory Postgres runtime.

This validates both migration application and repository contract parity on real Postgres.

## Rollback Guidance

- Schema migrations are forward-only; do not roll back by editing migration files.
- If rollout fails after migration:
  - keep schema as-is,
  - redeploy previous compatible app version,
  - fix forward in a new migration.
- If startup fails due runtime guardrails:
  - correct backend/DSN env configuration,
  - rerun `scripts/production_cutover_check.py --check-migrations`,
  - restart services.

## Completion Evidence

- Production cutover evidence should be recorded in the active advisory rollout documentation for the release being deployed.
