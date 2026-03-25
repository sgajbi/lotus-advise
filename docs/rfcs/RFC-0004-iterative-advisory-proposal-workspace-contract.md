# RFC-0004: Iterative Advisory Proposal Workspace Contract

- Status: PROPOSED
- Date: 2026-02-24
- Owners: lotus-advise advisory workflow service

## Problem Statement

Advisors need an iterative build-refine-evaluate loop that supports repeated trade and cash
adjustments with immediate constraint and portfolio-impact feedback. Current workflow APIs are
closer to run submission than interactive workspace collaboration.

## Root Cause

- Existing contracts emphasize simulation runs and lifecycle transitions, not iterative workspace state.
- No dedicated delta-based contract for interactive proposal editing.
- Constraint, suitability, and impact feedback are not normalized for per-iteration UI panels.

## Proposed Solution

1. Introduce iterative proposal workspace contracts:
   - draft workspace session
   - add, update, and remove delta actions
   - evaluate current draft against policy, suitability, and downstream analytics seams
2. Return normalized impact and violation models optimized for Lotus Workbench UI guidance.
3. Preserve current proposal lifecycle APIs for formal progression to approval and execution.

## Architectural Impact

- Better alignment with advisory workflow behavior expected by private banking users.
- Requires stronger idempotency and deterministic draft-state replay.
- Prepares `lotus-advise` for stateful portfolio sourcing and richer multi-service orchestration.

## Risks and Trade-offs

- Session and state complexity increases in the advisory API model.
- Additional persistence and audit requirements are needed for draft iteration history.
- UI and API contracts must remain tightly aligned to avoid interaction drift.

## High-Level Implementation Approach

1. Define draft session schema and mutation endpoints.
2. Add normalized constraint and impact response contracts.
3. Add replay-safe persistence strategy for draft iterations.
4. Add end-to-end tests with `lotus-gateway` and `lotus-workbench`.

## Dependencies

- Consumed by Lotus Workbench and gateway advisory workflows.
- Integrates with `lotus-core` stateful sourcing and optional downstream analytics seams.

