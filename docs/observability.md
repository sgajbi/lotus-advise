# Lotus Advise Observability

This document records the current observability baseline and gaps for the hardening program.

## Current Baseline

- Correlation IDs are used in key advisory workflows and advisory-copilot operations.
- Persistence, lineage, idempotency, and review records carry audit context for governed advisory
  workflows.
- Runtime smoke commands exist for Postgres runtime contracts and production-profile guardrail
  negatives.

## Current Gaps

- Structured logging, metrics, tracing, readiness/liveness separation, and operational diagnostics
  need a complete cross-service inventory before strict enforcement.
- Observability gates are not yet part of the new quality baseline workflow.
- Dashboard, alert, and SLO evidence is not yet captured in repo-local artifacts.

## Next Steps

- Inventory API and background workflow correlation coverage.
- Add report-only diagnostics checks before enforcing observability thresholds.
- Keep sensitive data out of logs and diagnostic artifacts.
