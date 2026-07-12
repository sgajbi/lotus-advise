# Advisory Workspace

## Purpose

The advisory workspace supports iterative draft preparation before formal lifecycle ownership begins.

It gives advisors a place to:

- start from normalized stateful context
- add or adjust draft actions
- re-evaluate a draft deterministically
- save checkpoints
- resume prior versions
- compare current work against a saved baseline
- hand off into the persisted proposal lifecycle

## Why It Exists

The workspace keeps exploratory drafting separate from formal proposal persistence. That separation matters for:

- cleaner operator workflows
- explicit evidence continuity
- controlled lifecycle ownership
- replay-safe support paths

## Application Boundary

Workspace API routes delegate workflow behavior to the Advise workspace application service.

| Boundary | Current Owner |
| --- | --- |
| HTTP mapping and safe errors | `src/api/workspaces` |
| Workspace use cases | `src/core/workspace/application.py` |
| Repository, source-context, evaluator, and lifecycle ports | `src/core/workspace/ports.py` |
| Lotus Core source-context adapter | `src/infrastructure/workspace/lotus_core_context.py` |
| Process-local workspace session adapter | `src/infrastructure/workspace/in_memory.py` |
| Durable workspace schema foundation | `src/infrastructure/postgres_migrations/workspace/0001_workspace_state.sql` |

This is a design-modularity improvement inside one Advise backend service. It is not a new runtime
service split. Durable workspace repository wiring, restart recovery, and scale-out proof remain
staged work; the current runtime still composes the process-local workspace session adapter.

## AI Support

The implemented AI-facing workspace integration boundary is:

- `POST /advisory/workspaces/{workspace_id}/assistant/rationale`

This endpoint returns an evidence-grounded workspace rationale and includes the deterministic evidence bundle supplied to the AI workflow.

That is different from the RFC-0023 proposal narrative capability, which is implemented for
advisor-review artifact, review/replay, reviewed report-request package, report/render/archive,
Gateway posture, and Workbench posture. Client-ready proposal narrative remains gated.

## Lifecycle Handoff

`POST /advisory/workspaces/{workspace_id}/handoff` persists a workspace draft into formal lifecycle ownership.

- first handoff creates a proposal
- later handoffs create new versions

This keeps the workspace as a drafting surface, not a second lifecycle system.
