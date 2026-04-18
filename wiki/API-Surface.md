# API Surface

## Health

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

## Advisory Simulation

- `POST /advisory/proposals/simulate`
- `POST /advisory/proposals/artifact`

These endpoints accept normalized advisory input contracts and require `Idempotency-Key`. They are the core deterministic simulation and artifact entry points.

## Advisory Proposal Lifecycle

- `POST /advisory/proposals`
- `GET /advisory/proposals`
- `GET /advisory/proposals/{proposal_id}`
- `GET /advisory/proposals/{proposal_id}/versions/{version_no}`
- `POST /advisory/proposals/{proposal_id}/versions`
- `POST /advisory/proposals/{proposal_id}/transitions`
- `POST /advisory/proposals/{proposal_id}/approvals`
- `POST /advisory/proposals/{proposal_id}/report-requests`
- `POST /advisory/proposals/{proposal_id}/execution-handoffs`
- `POST /advisory/proposals/{proposal_id}/execution-updates`

## Advisory Operations And Support

- `GET /advisory/proposals/{proposal_id}/delivery-summary`
- `GET /advisory/proposals/{proposal_id}/delivery-events`
- `GET /advisory/proposals/{proposal_id}/execution-status`

These support surfaces derive operator-facing posture from append-only workflow history.

## Advisory Workspace

- `POST /advisory/workspaces`
- `GET /advisory/workspaces/{workspace_id}`
- `POST /advisory/workspaces/{workspace_id}/draft-actions`
- `POST /advisory/workspaces/{workspace_id}/evaluate`
- `POST /advisory/workspaces/{workspace_id}/save`
- `GET /advisory/workspaces/{workspace_id}/saved-versions`
- `GET /advisory/workspaces/{workspace_id}/saved-versions/{workspace_version_id}/replay-evidence`
- `POST /advisory/workspaces/{workspace_id}/resume`
- `POST /advisory/workspaces/{workspace_id}/compare`
- `POST /advisory/workspaces/{workspace_id}/assistant/rationale`
- `POST /advisory/workspaces/{workspace_id}/handoff`

## Contract Notes

- OpenAPI is the governed external contract.
- REST remains the current contract posture; this service does not justify gRPC today.
- Lifecycle and support routes can be feature-gated by runtime flags.
- Readiness should fail closed when required upstream execution authority is not correctly configured.
