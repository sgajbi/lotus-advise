# Lotus Advise Architecture Rules

## Enforcement Phase

- Current phase: enforced clean import-linter contracts.
- Direction: expand architecture-boundary contracts only after each new boundary is proven clean
  locally and in GitHub CI.

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

- `.importlinter` defines enforced contracts for API-to-infrastructure, core-to-FastAPI, and
  infrastructure-to-API dependency boundaries.
- `make architecture-boundaries` runs import-linter against `.importlinter`.
- `make lint` carries `make architecture-boundaries` into Feature Lane, PR Merge Gate, and Main
  Releasability.
- `quality/baseline_report.md` records the import-linter contract inventory for before/after
  scorecard evidence.

## Next Gate

- Add new import-linter contracts only after source dependencies are clean enough for absolute
  enforcement.
- Keep workflow contract tests pinned to the `make lint` inheritance path so architecture
  enforcement cannot drift out of CI silently.
