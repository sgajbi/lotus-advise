# Project Overview

This document explains the system at a high level for three audiences:
- business stakeholders,
- business analysts (BAs),
- developers.

## What This Platform Does

The platform provides advisory workflow APIs for:
- advisory proposal simulation from advisor-entered cash flows and manual trades,
- proposal lifecycle progression for review, approval, consent, and execution readiness,
- advisory-facing orchestration seams for Lotus platform integrations.

Architecture authority:
- Platform-wide integration and architecture standards are maintained centrally in `https://github.com/sgajbi/lotus-platform`.
- This repository documents service-local implementation details and service-specific RFCs only.

Current advisory flows produce structured, auditable outputs with:
- before/after portfolio states,
- intent-level actions,
- rules and diagnostics,
- lineage identifiers and deterministic hashes.

Target operating model:
- `lotus-advise` owns advisory workflow orchestration and proposal lifecycle,
- `lotus-core` owns canonical portfolio state and portfolio simulation authority,
- `lotus-risk` owns risk analytics,
- `lotus-report` owns reporting outputs,
- `lotus-ai` provides governed AI infrastructure for advisor-assistive features.

## Why It Matters

For business and control functions, the platform is built for:
- reproducibility,
- explainability,
- policy-based controls,
- workflow readiness.

Domain outcomes are returned as:
- `READY`
- `PENDING_REVIEW`
- `BLOCKED`

The API remains deterministic for identical inputs and options.

## Core Business Flows

1. Advisory proposal simulation
- Input: portfolio snapshot, market snapshot, shelf, advisor cash/trade proposals, options.
- Output: proposal simulation plus optional artifact package for client/reviewer workflow.
- Authority posture: runtime simulation authority is delegated to `lotus-core` through a versioned
  canonical execution contract, while `lotus-advise` continues to own advisory request
  normalization, workflow orchestration, and proposal lifecycle semantics.
- Contract governance: the `lotus-core` simulation seam is pinned to
  `X-Lotus-Contract-Version: advisory-simulation.v1`, and the returned lineage must carry the same
  `simulation_contract_version` for replay-safe parity.
- Stateful context resolution: identifier-based advisory requests resolve portfolio state through
  the Lotus Core query surface. When `LOTUS_CORE_QUERY_BASE_URL` is not set explicitly,
  `lotus-advise` derives the query endpoint from `LOTUS_CORE_BASE_URL` so canonical execution and
  state resolution remain aligned in local and containerized runtime setups.
- Stateful draft enrichment: stateful workspace evaluation now enriches newly drafted instruments
  from Lotus Core query data when they are not already present in the source holdings snapshot,
  allowing advisor trade drafting to stay identifier-based without forcing clients to inline market
  and shelf payloads for each new instrument.
- Fallback posture: local advisory execution is no longer a normal runtime mode. It is retained
  only as a controlled non-production fallback and test oracle behind
  `LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK`.
- Environment quarantine: the controlled fallback is permitted only in local/dev/test-style
  environments. Production-style environments must use `lotus-core` simulation authority.

2. Advisory proposal lifecycle
- Input: simulated proposal payloads plus workflow actor actions.
- Output: persisted proposal versions, approvals, consent state, execution readiness, and
  lifecycle provenance showing whether a proposal originated directly or through workspace handoff.
- Audit/supportability reads expose lifecycle summaries, lineage completeness, and deterministic
  workflow and approval context for investigation flows.

3. Workflow semantics
- Gate decisions provide deterministic next-step semantics:
  - blocked,
  - risk review,
  - compliance review,
  - client consent,
  - execution ready.

## API Surface

- `POST /advisory/proposals/simulate`
- `POST /advisory/proposals/artifact`
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
- `POST /advisory/proposals`
- `GET /advisory/proposals`
- `GET /advisory/proposals/{proposal_id}`
- `POST /advisory/proposals/{proposal_id}/report-requests`
- `POST /advisory/proposals/{proposal_id}/execution-handoffs`
- `GET /advisory/proposals/{proposal_id}/execution-status`
- `GET /platform/capabilities`

## Architecture Summary

- `src/api/`: FastAPI contracts and endpoint orchestration.
- `src/api/proposals/`: proposal lifecycle API package for runtime wiring, errors, and lifecycle/async/support routes.
- `src/api/workspaces/`: advisory workspace API package for workspace session contract entry points.
- `src/core/advisory/`: advisory-specific modules (artifact, funding, intents, ids, orchestration).
- `src/core/common/`: Shared logic (simulation primitives, diagnostics, drift, suitability, canonical hashing, workflow gates).
- `src/core/proposals/`: proposal lifecycle models, services, and repository abstractions.
- `src/core/workspace/`: advisory workspace contract models for stateless/stateful draft sessions and evaluation summaries.
- `src/integrations/`: adapter seams for Lotus platform dependencies.
- `src/integrations/lotus_core/context_resolution.py`: explicit stateful advisory context seam used to resolve replay-safe portfolio evaluation context from Lotus Core.
- `src/integrations/lotus_core/simulation.py`: explicit Lotus Core simulation authority seam for advisory proposal evaluation.
  - The canonical upstream execution contract is versioned and validated through
    `X-Lotus-Contract-Version`.
  - When the seam is unavailable, `lotus-advise` returns an upstream dependency error unless the
    controlled local fallback switch is explicitly enabled.
- `src/integrations/lotus_risk/enrichment.py`: explicit Lotus Risk enrichment seam for advisory proposal evaluation.
- `src/integrations/lotus_ai/rationale.py`: explicit Lotus AI rationale seam for evidence-grounded workspace assistance.
- `src/integrations/lotus_report/adapter.py`: explicit Lotus Report seam for advisory report requests without moving reporting ownership into lotus-advise.
- `src/api/capabilities/`: readiness and capability resolution seams for integration-aware platform truth.
- `src/core/models.py`: shared request/response contracts and options.

Advisory persistence boundary:
- Active PostgreSQL persistence is proposal-lifecycle-focused and currently owns:
  - `proposal_records`
  - `proposal_versions`
  - `proposal_workflow_events`
  - `proposal_approvals`
  - `proposal_idempotency`
  - `proposal_simulation_idempotency`
  - `proposal_async_operations`
- Workspace sessions and saved workspace versions remain intentionally non-durable in the current
  runtime slice until later advisory persistence work lands.
- Portfolio positions, transactions, market data, risk analytics, reports, and shared AI runtime
  state are upstream-owned and excluded from the advisory database boundary.
- External execution-provider state also remains upstream-owned; lotus-advise only records
  advisory handoff and execution-correlation metadata through workflow history.
- API startup now validates proposal repository boot readiness, so lifecycle PostgreSQL
  connectivity and migration application fail fast before the service begins serving requests.
- Canonical simulation contract mismatches and validation failures are surfaced as problem-details
  responses so downstream callers can distinguish dependency outages from contract drift.

## Test Strategy

Tests are organized by responsibility:
- `tests/unit/advisory/`: advisory API, engine, contracts, and advisory golden tests.
- `tests/unit/shared/`: shared contracts/compliance/dependencies tests.
- `tests/e2e/`: end-to-end workflow/demo scenario tests.
- `tests/shared/`: shared test helpers (factories/assertions).

Golden fixtures and lifecycle scenarios should focus on advisory flows and shared invariants.

CI test execution model:
- runs `tests/unit`, `tests/integration`, and `tests/e2e` in parallel matrix jobs,
- combines per-suite coverage artifacts,
- enforces a single repository-wide `99%` coverage gate.

## Governance and RFCs

- RFCs under `docs/rfcs/` define scope and acceptance.
- `docs/rfcs/README.md` is the authoritative index for:
  - implemented RFCs,
  - active future work,
  - archived material that is no longer needed for active planning.
- Current implementation status is tracked in RFC metadata (`Status`, `Implemented In`).

## Current Delivery Principle

Keep `lotus-advise` advisory-only while sharing Lotus platform standards for:
- vocabulary,
- control semantics,
- deterministic primitives,
- test and audit standards.
