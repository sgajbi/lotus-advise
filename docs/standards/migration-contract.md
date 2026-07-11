# Migration Contract Standard

- Service: `lotus-advise`
- Persistence mode: PostgreSQL with forward-only SQL migration packs.
- Migration policy: versioned migrations with checksum validation and namespace-scoped locking.
- Current namespaces: `proposals`, `advisory_copilot`, `policy_packs`.
- Rollout policy: every migration must be represented in
  `docs/standards/postgres-migration-rollout-contract.v1.json` with explicit expand/migrate/contract
  phase, old/new application compatibility, lock and online behavior, backfill posture, rollback
  limits, and non-production rehearsal evidence.

## Deterministic Checks

- `make migration-rollout-contract-gate` validates rollout metadata against the checked-in SQL
  files and emits `output/postgres-migration-rollout-rehearsal.json`.
- `make migration-smoke` executes migration contract unit tests.
- CI also runs dedicated migration smoke in workflow.

## Apply Command

- `make migration-apply` runs `python scripts/postgres_migrate.py --target all`.
- Per-namespace runs use `--target proposals`, `--target advisory_copilot`, or
  `--target policy_packs`.

## Rollback and Forward-Fix

- Applied migration files are immutable.
- Rollback strategy is forward-fix with a new migration plus cutover validation.
- Existing non-concurrent index migrations require controlled rollout windows and production-like
  rehearsal evidence. Do not describe them as online/concurrent unless the SQL uses
  `CREATE INDEX CONCURRENTLY` and the migration runner supports the required transaction behavior.
