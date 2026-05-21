# Troubleshooting

## Readiness Fails

If `/health/ready` fails:

1. verify advisory persistence configuration
2. verify proposal repository connectivity
3. verify Postgres DSN and runtime profile inputs

Typical readiness failures are persistence-contract or connection problems, not just transient HTTP issues.

## Proposal Behavior Looks Wrong

Check upstream posture first:

1. `LOTUS_CORE_BASE_URL`
2. `LOTUS_CORE_QUERY_BASE_URL`
3. `LOTUS_RISK_BASE_URL`
4. `LOTUS_RISK_TIMEOUT_SECONDS`
5. `LOTUS_RISK_RETRY_ATTEMPTS`
6. `LOTUS_RISK_RETRY_BACKOFF_SECONDS`

`lotus-advise` depends on canonical source-data, simulation, and risk enrichment authorities.
For Lotus Risk enrichment, retry attempts are intentionally capped at `5` and retry backoff at
`2.0` seconds so a misconfigured environment cannot create unbounded advisory latency.

## Decision Summary Or Alternatives Drift

Treat this as a contract issue until proven otherwise.

Review:

1. lifecycle persistence behavior
2. canonical and degraded live evidence
3. RFC-0082 upstream coupling
4. proposal workspace and replay continuity

## Migration Or Startup Issues

Use the Postgres rollout runbook:

- `docs/documentation/postgres-migration-rollout-runbook.md`
