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

## AI Support

The implemented AI-facing workspace seam is:

- `POST /advisory/workspaces/{workspace_id}/assistant/rationale`

This endpoint returns an evidence-grounded workspace rationale and includes the deterministic evidence bundle supplied to the AI workflow.

That is different from the broader proposal narrative capability described in RFC-0023, which remains future work.

## Lifecycle Handoff

`POST /advisory/workspaces/{workspace_id}/handoff` persists a workspace draft into formal lifecycle ownership.

- first handoff creates a proposal
- later handoffs create new versions

This keeps the workspace as a drafting surface, not a second lifecycle system.
