# RFC-0027: Advisory Proposal Workflow Coverage Hardening (Approval Chain Paths)

| Field | Value |
| --- | --- |
| Status | IMPLEMENTED |
| Created | 2026-02-22 |
| Depends On | RFC-0014G, RFC-0024 |

## 1. Context

Proposal lifecycle already supports risk/compliance/client-consent transitions, but test coverage favored compliance-first path. We need stronger regression protection for risk-first and rejection terminal paths.

## 2. Decision

Add deterministic API tests for:

- risk-first happy path: `DRAFT -> RISK_REVIEW -> AWAITING_CLIENT_CONSENT -> EXECUTION_READY`
- rejection path: `DRAFT -> RISK_REVIEW -> REJECTED`
- guardrail after terminal state: invalid further transition returns `INVALID_TRANSITION`

## 3. Acceptance Criteria

- New tests pass in unit API suite.
- Existing lifecycle tests remain green.
- No contract change required.

## 4. Notes

This RFC is coverage hardening only; it does not change lifecycle API shape.
