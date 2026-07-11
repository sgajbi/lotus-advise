# Lotus Advise Observability

This document records the current observability baseline and gaps for the hardening program.

## Current Baseline

- Correlation IDs are used in key advisory workflows and advisory-copilot operations.
- HTTP middleware propagates correlation, request, and trace identifiers to responses.
- Structured JSON logs include service, environment, correlation, request, trace, route-template,
  operation-name, status, and latency context.
- HTTP request-completed logs use bounded FastAPI route templates, not raw URL paths, for
  `endpoint`, `route_template`, and `operation_name`.
- Enterprise audit actions use bounded operation names such as
  `POST /advisory/proposals/{proposal_id}/versions/{version_no}/reviews`; raw proposal,
  workspace, policy-evaluation, operation, portfolio, client, or account identifiers must not be
  emitted in action strings or metric/log labels.
- Prometheus instrumentation exposes runtime metrics through the FastAPI instrumentation layer.
- Persistence, lineage, idempotency, and review records carry audit context for governed advisory
  workflows.
- Runtime smoke commands exist for Postgres runtime contracts and production-profile guardrail
  negatives.
- `make observability-diagnostics` verifies the current request/trace/log propagation contract.

## Telemetry Field Contract

Allowed request log aggregation fields:

- `http_method`
- `endpoint` as a route template
- `route_template`
- `operation_name`
- `http_status_code`
- `http_status_class`
- `latency_ms`

Raw URL paths and business identifiers are only allowed in separately governed, support-safe
diagnostic evidence with explicit redaction and retention controls. They are forbidden as default
log fields, metric labels, dashboard dimensions, alert dimensions, and enterprise audit action
strings.

## Current Gaps

- Dashboard, alert, SLO, and distributed-tracing evidence need a complete cross-service inventory
  before strict enforcement.
- Dashboard, alert, and SLO evidence is not yet captured in repo-local artifacts.
- Cross-service dashboards should aggregate by `operation_name`, `http_status_class`, dependency,
  and supportability reason code, not by raw path or resource id.

## Next Steps

- Inventory API and background workflow correlation coverage.
- Expand diagnostics beyond HTTP middleware into background workflows and downstream integration
  calls.
- Keep sensitive data out of logs and diagnostic artifacts.
