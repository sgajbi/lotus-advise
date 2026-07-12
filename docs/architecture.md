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

## Advisory Workspace Application Boundary

The advisory workspace routes are thin HTTP adapters over `WorkspaceApplicationService`.

- `src/api/workspaces` maps request DTOs, headers, and proposal/workspace HTTP errors.
- `src/core/workspace/application.py` owns workspace create, get, draft-action, re-evaluate,
  save, replay, resume, compare, and lifecycle-handoff use cases.
- `src/core/workspace/ports.py` defines the workspace session repository, source-context resolver,
  proposal evaluator, and proposal lifecycle ports.
- `src/infrastructure/workspace` contains the current Lotus Core source-context resolver and the
  in-memory workspace session repository adapter.
- `src/infrastructure/postgres_migrations/workspace` contains the durable workspace state schema
  foundation for sessions, saved versions, audit events, and idempotency evidence.
- `src/runtime/workspace_application.py` composes the process-local application service.

This is an internal design-modularity boundary. It does not create a separate deployable workspace
service. Durable workspace repository wiring, recovery proof, and broader idempotency controls
remain staged backlog work until the workspace Postgres adapter is composed at runtime.

## Current Quality Posture

- Existing gates include ruff, mypy, OpenAPI quality, no-alias, API vocabulary, data-product
  declarations, dependency health, security audit, coverage, migration smoke, and runtime smoke
  checks.
- New architecture-boundary rules are documented in `quality/architecture_rules.md` and configured
  in `.importlinter` for report-only rollout.
- This document does not claim final bank certification, external compliance approval, or full
  enterprise-readiness closure.
