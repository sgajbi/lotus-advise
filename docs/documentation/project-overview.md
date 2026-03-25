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

2. Advisory proposal lifecycle
- Input: simulated proposal payloads plus workflow actor actions.
- Output: persisted proposal versions, approvals, consent state, and execution readiness.

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
- `POST /advisory/workspaces/{workspace_id}/handoff`
- `POST /advisory/proposals`
- `GET /advisory/proposals`
- `GET /advisory/proposals/{proposal_id}`

## Architecture Summary

- `src/api/`: FastAPI contracts and endpoint orchestration.
- `src/api/proposals/`: proposal lifecycle API package for runtime wiring, errors, and lifecycle/async/support routes.
- `src/api/workspaces/`: advisory workspace API package for workspace session contract entry points.
- `src/core/advisory/`: Advisory-specific modules (artifact, funding, intents, ids).
- `src/core/common/`: Shared logic (simulation primitives, diagnostics, drift, suitability, canonical hashing, workflow gates).
- `src/core/proposals/`: proposal lifecycle models, services, and repository abstractions.
- `src/core/workspace/`: advisory workspace contract models for stateless/stateful draft sessions and evaluation summaries.
- `src/integrations/`: adapter seams for Lotus platform dependencies.
- `src/api/capabilities/`: readiness and capability resolution seams for integration-aware platform truth.
- `src/core/models.py`: shared request/response contracts and options.

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


