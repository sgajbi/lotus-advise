# Lotus Advise

Advisor-led proposal simulation and lifecycle service.

This repository contains advisory-only workflows.
It is focused on advisor proposal workflows, lifecycle state, approvals, consent, and execution readiness.

API docs endpoint: `/docs`

Local Docker runtime expects canonical upstream integrations to be explicit:

- `LOTUS_CORE_BASE_URL` should point at the lotus-core control-plane endpoint, for example `http://core-control.dev.lotus`
- `LOTUS_CORE_QUERY_BASE_URL` should point at the lotus-core query endpoint, for example `http://core-query.dev.lotus`
- `LOTUS_RISK_BASE_URL` should point at the lotus-risk API endpoint, for example `http://risk.dev.lotus`

This keeps proposal simulation and proposal risk-lens behavior aligned with the canonical service authorities during local Docker validation.
