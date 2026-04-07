# Lotus Advise

Advisor-led proposal simulation and lifecycle service.

This repository contains advisory-only workflows.
It is focused on advisor proposal workflows, lifecycle state, approvals, consent, and execution readiness.

API docs endpoint: `/docs`

Local Docker runtime expects canonical upstream integrations to be explicit:

- `LOTUS_CORE_BASE_URL` should point at the lotus-core control-plane endpoint, for example `http://host.docker.internal:8202`
- `LOTUS_RISK_BASE_URL` should point at the lotus-risk API endpoint, for example `http://host.docker.internal:8130`

This keeps proposal simulation and proposal risk-lens behavior aligned with the canonical service authorities during local Docker validation.
