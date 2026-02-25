# Migration Contract Standard

- Service: `dpm-rebalance-engine`
- Persistence mode: PostgreSQL with forward-only SQL migration packs.
- Migration policy: versioned migrations with checksum validation and namespace-scoped locking.

## Deterministic Checks

- `make migration-smoke` executes migration contract unit tests.
- CI also runs dedicated migration smoke in workflow.

## Apply Command

- `make migration-apply` runs `python scripts/postgres_migrate.py --target all`.

## Rollback and Forward-Fix

- Applied migration files are immutable.
- Rollback strategy is forward-fix with a new migration plus cutover validation.
