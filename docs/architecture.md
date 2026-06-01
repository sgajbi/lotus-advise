# Lotus Advise Architecture

Lotus Advise is the advisory domain API for proposal, policy, memo, cockpit, delivery, and
advisory-copilot workflows. The current hardening direction is to keep API routers thin, move
business behavior into application/core services, and isolate infrastructure behind repository and
adapter boundaries.

## Current Boundary Model

- `src/api` owns FastAPI routes, request parameter wiring, HTTP status mapping, and dependency
  injection.
- `src/core` owns advisory domain models, application services, validation, lineage, idempotency,
  persistence-facing records, and business policy.
- `src/infrastructure` owns in-memory and Postgres adapters and runtime integration details.
- `scripts` owns repo-governance, quality, OpenAPI, dependency, migration, and runtime validation
  automation.

## Current Quality Posture

- Existing gates include ruff, mypy, OpenAPI quality, no-alias, API vocabulary, data-product
  declarations, dependency health, security audit, coverage, migration smoke, and runtime smoke
  checks.
- New architecture-boundary rules are documented in `quality/architecture_rules.md` and configured
  in `.importlinter` for report-only rollout.
- This document does not claim final bank certification, external compliance approval, or full
  enterprise-readiness closure.
