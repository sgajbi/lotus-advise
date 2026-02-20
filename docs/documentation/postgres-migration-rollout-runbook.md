# PostgreSQL Migration Rollout Runbook

## Scope

Runbook for forward-only schema migration rollout for:

- DPM supportability Postgres namespace (`dpm`)
- Advisory proposals Postgres namespace (`proposals`)

## Preconditions

- PostgreSQL is reachable and healthy.
- Runtime DSNs are configured:
  - `DPM_SUPPORTABILITY_POSTGRES_DSN`
  - `PROPOSAL_POSTGRES_DSN`
- Application image/version to deploy is already tested in non-production.

## Migration Command

Use the shared migration tool before switching traffic:

```bash
python scripts/postgres_migrate.py --target all
```

Optional per-namespace commands:

```bash
python scripts/postgres_migrate.py --target dpm
python scripts/postgres_migrate.py --target proposals
```

## Startup Sequencing

1. Start/verify Postgres instance health.
2. Apply migrations (`scripts/postgres_migrate.py`).
3. Start API services with Postgres backends enabled.
4. Run smoke API checks for DPM and advisory.
5. Shift traffic.

Do not start app replicas with Postgres backend enabled before migrations have completed.

## Safety Controls

- Migrations are forward-only.
- Applied migration checksums are stored in `schema_migrations`.
- Migration execution is wrapped in a namespace-scoped PostgreSQL advisory lock
  to avoid concurrent deploy races.
- If a checked-in migration file is modified after apply, execution fails with:
  - `POSTGRES_MIGRATION_CHECKSUM_MISMATCH:{namespace}:{version}`

## CI Smoke Checks

CI executes:

1. `python scripts/postgres_migrate.py --target all`
2. Live Postgres integration tests:
   - `tests/dpm/supportability/test_dpm_postgres_repository_integration.py`
   - `tests/advisory/engine/test_engine_proposal_repository_postgres_integration.py`

This validates both migration application and repository contract parity on real Postgres.

## Rollback Guidance

- Schema migrations are forward-only; do not roll back by editing migration files.
- If rollout fails after migration:
  - keep schema as-is,
  - redeploy previous compatible app version,
  - fix forward in a new migration.

## Completion Evidence

- Cutover acceptance checklist:
  - `docs/demo/postgres-cutover-checklist-2026-02-20.md`
