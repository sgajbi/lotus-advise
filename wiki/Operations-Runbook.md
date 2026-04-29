# Operations Runbook

## Health Endpoints

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

## Readiness Meaning

Readiness is not a cosmetic check. Startup and readiness validate:

1. advisory runtime persistence posture
2. proposal repository boot readiness
3. proposal async runtime recovery posture

If the service cannot satisfy the advisory persistence contract, readiness should fail closed.

## Advisory Supportability Metrics

`GET /platform/capabilities` publishes the implemented feature key
`advise.observability.advisory_supportability` and a source-backed `supportability` summary. The
summary reports only bounded operational posture:

1. `state`
2. `reason`
3. `freshness_bucket`
4. dependency and feature readiness counts

`/metrics` emits `lotus_advise_advisory_supportability_total` with `state`, `reason`, and
`freshness_bucket` labels only. Do not add portfolio, client, request, response, correlation, or
trace identifiers to this metric.

## Canonical Local Identity

Use:

- `http://advise.dev.lotus`

That is the canonical local service identity for cross-app and demo-oriented flows.

## Postgres Rollout Notes

The active runtime direction is PostgreSQL-backed proposal lifecycle persistence.

Operationally important commands from the rollout runbook:

```bash
python scripts/postgres_migrate.py --target all
python scripts/production_cutover_check.py --check-migrations
```

Use the full runbook in `docs/documentation/postgres-migration-rollout-runbook.md` for rollout,
smoke, and fix-forward guidance.
