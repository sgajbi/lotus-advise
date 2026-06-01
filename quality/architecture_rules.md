# Lotus Advise Architecture Rules

## Enforcement Phase

- Current phase: baseline/report-only.
- Direction: move from report-only to fail-on-new-regression, then enforce agreed thresholds.

## Boundary Rules

- API routers call application services or use cases only.
- API routers must not call repositories, database clients, HTTP clients, Kafka, Redis, or
  downstream adapters directly.
- Middleware stays thin and business-logic-free.
- Core domain and application modules must not depend on FastAPI, Starlette, framework request
  objects, infrastructure clients, or persistence adapters.
- Infrastructure sits behind repository, gateway, or adapter ports.
- DTOs and persistence models must not leak into domain decision logic.

## Current Evidence

- `.importlinter` defines report-only contracts for API-to-infrastructure, core-to-FastAPI, and
  infrastructure-to-API dependency boundaries.
- `quality/baseline_report.md` records architecture-boundary status as a current report-only gap
  until import-linter is installed and calibrated.

## Next Gate

- Install and run import-linter in CI as report-only.
- Baseline current violations, if any.
- Move to fail-on-new-regression before enforcing absolute architecture thresholds.
