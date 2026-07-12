# Scalability and Availability Standard Alignment

Service: lotus-advise

This repository adopts the platform-wide standard defined in lotus-platform/Scalability and Availability Standard.md.

## Implemented Baseline

- Stateless service behavior with externalized durable state.
- Explicit timeout and bounded retry/backoff for inter-service communication where applicable.
- Health/liveness/readiness endpoints for runtime orchestration.
- Observability instrumentation for latency/error/throughput diagnostics.

## Required Evidence

- Compliance matrix entry in lotus-platform/output/scalability-availability-compliance.md.
- Service-specific tests covering resilience and concurrency-critical paths.
- Machine-readable SLO and capacity budget contract:
  `docs/standards/advisory-slo-capacity-budgets.v1.json`.
- Repo-native validation gate: `make slo-capacity-gate`.
- Machine-readable durable-state recovery contract:
  `docs/standards/advisory-durable-state-recovery.v1.json`.
- Repo-native recovery scope and drill-evidence gate: `make durable-state-recovery-gate`.

## Database Scalability Fundamentals

- Query plan review is required for proposal retrieval, run supportability, and operation lookup endpoints.
- Index definitions must support correlation-id, workflow status, and time-window query paths.
- Data growth assumptions are tracked for async operation logs and persisted run artifacts.
- Retention and archival controls are mandatory for supportability records and audit-linked payloads.

## Availability Baseline

- Internal SLO baseline: p95 synchronous proposal API latency < 400 ms; error rate < 1%.
- Recovery targets: RTO 30 minutes and RPO 15 minutes for persisted lotus-advise operations.
- Backup and restore validation is required for proposal/run stores in every deployment environment.
- Durable recovery scope covers `proposals`, `policy_packs`, `advisory_copilot`, and `workspace`
  migration namespaces. Platform database operations own backup vendor and point-in-time restore;
  Advise owns post-restore integrity, replay, idempotency, quarantine, and evidence checks.

## Advisory Workflow SLO And Capacity Budgets

`docs/standards/advisory-slo-capacity-budgets.v1.json` is the source of truth for endpoint and
workflow budgets. It defines:

- workflow availability, p95/p99 latency, timeout, correctness/degraded-rate, and concurrency
  targets,
- Lotus Core, Risk, Report, AI, Performance, and PostgreSQL timeout, retry, rate, and error
  budgets,
- AI input-token, output-token, per-request cost, and fallback ceilings,
- allowed bounded metric dimensions and forbidden high-cardinality or sensitive dimensions,
- alert/runbook mappings,
- representative local and dependency-injection load-smoke profiles.

`make slo-capacity-gate` validates the contract and emits
`output/slo-capacity-smoke-plan.json` for automation that runs live load/capacity smoke evidence.
`make check`, `make ci`, and `make ci-local` include this gate.

## Caching Policy Baseline

- lotus-advise only permits explicit bounded caches for idempotency and workflow supportability lookups.
- Cache use-cases must define TTL and max-size controls with clear invalidation ownership.
- Stale-read behavior is disallowed for correctness-critical advisory proposal outcomes; stale supportability reads must be explicitly documented.

## Scale Signal Metrics Coverage

- lotus-advise exports `/metrics` for HTTP and workflow instrumentation.
- Platform-shared infrastructure metrics for CPU/memory, DB latency/pool behavior, and queue lag are sourced from:
  - `lotus-platform/platform-stack/prometheus/prometheus.yml`
  - `lotus-platform/platform-stack/docker-compose.yml`
  - `lotus-platform/Platform Observability Standards.md`

## Deviation Rule

Any deviation from this standard requires ADR/RFC with remediation timeline.

