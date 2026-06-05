# Lotus Advise Observability

This document records the current observability baseline and gaps for the hardening program.

## Current Baseline

- Correlation IDs are used in key advisory workflows and advisory-copilot operations.
- HTTP middleware propagates correlation, request, and trace identifiers to responses.
- Structured JSON logs include service, environment, correlation, request, trace, endpoint, and
  latency context.
- Prometheus instrumentation exposes runtime metrics through the FastAPI instrumentation layer.
- Persistence, lineage, idempotency, and review records carry audit context for governed advisory
  workflows.
- Runtime smoke commands exist for Postgres runtime contracts and production-profile guardrail
  negatives.
- `make observability-diagnostics` verifies the current request/trace/log propagation contract.

## Current Gaps

- Dashboard, alert, SLO, and distributed-tracing evidence need a complete cross-service inventory
  before strict enforcement.
- Dashboard, alert, and SLO evidence is not yet captured in repo-local artifacts.

## Next Steps

- Inventory API and background workflow correlation coverage.
- Expand diagnostics beyond HTTP middleware into background workflows and downstream integration
  calls.
- Keep sensitive data out of logs and diagnostic artifacts.
