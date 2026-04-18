# API Surface

## Surface groups

`lotus-advise` exposes four practical groups:

1. simulation
2. proposal lifecycle and support
3. workspace
4. integration and health

## Simulation

- `POST /advisory/proposals/simulate`
- `POST /advisory/proposals/artifact`

## Proposal lifecycle and support

This repo also exposes persisted proposal lifecycle, async, delivery, support, report request, and
execution handoff routes through the proposal router package under `src/api/proposals/`.

Use the deep docs and OpenAPI surface for endpoint-by-endpoint payload detail.

## Workspace

Core workspace routes include:

- `POST /advisory/workspaces`
- `GET /advisory/workspaces/{workspace_id}`
- `POST /advisory/workspaces/{workspace_id}/draft-actions`
- `POST /advisory/workspaces/{workspace_id}/evaluate`
- `POST /advisory/workspaces/{workspace_id}/save`
- `GET /advisory/workspaces/{workspace_id}/saved-versions`
- `POST /advisory/workspaces/{workspace_id}/resume`
- `POST /advisory/workspaces/{workspace_id}/compare`
- `POST /advisory/workspaces/{workspace_id}/assistant/rationale`
- `POST /advisory/workspaces/{workspace_id}/handoff`

## Integration and health

- platform capability and readiness surface via `src/api/routers/integration_capabilities.py`
- `/health`
- `/health/live`
- `/health/ready`
- `/docs`

## Where to go next

- project overview:
  [docs/documentation/project-overview.md](../docs/documentation/project-overview.md)
- upstream contract map:
  [Integrations](Integrations)
