# Repository Engineering Context

This file provides repository-local engineering context for `lotus-advise`.

For platform-wide truth, read:

1. `C:\Users\Sandeep\projects\lotus-platform\context\LOTUS-QUICKSTART-CONTEXT.md`
2. `C:\Users\Sandeep\projects\lotus-platform\context\LOTUS-ENGINEERING-CONTEXT.md`
3. `C:\Users\Sandeep\projects\lotus-platform\context\CONTEXT-REFERENCE-MAP.md`

## Repository Role

`lotus-advise` is the advisory workflow and proposal simulation service.

It owns advisor-led proposal lifecycle and recommendation-oriented execution readiness behavior.

## Business And Domain Responsibility

This repository owns:

1. advisor-led proposal simulation,
2. proposal lifecycle state,
3. advisory approvals and consent-related workflow behavior,
4. advisory execution readiness.

It does not own discretionary portfolio-management operations; those belong to `lotus-manage`.

## Current-State Summary

Current repository posture:

1. `lotus-advise` is now scoped to advisory-only workflows after the split from `lotus-manage`,
2. runtime smoke and production-profile guardrail validation are part of the real CI contract,
3. canonical upstream integration with `lotus-core` and `lotus-risk` matters for truthful proposal behavior,
4. repo-native CI is already aligned to explicit lane expectations.

## Architecture And Module Map

Primary areas:

1. `src/`
   advisory APIs, workflow logic, and supporting modules.
2. `scripts/`
   dependency-health, runtime smoke, OpenAPI, vocabulary, and governance scripts.
3. `docs/`
   advisory standards and workflow documentation.
4. `tests/`
   unit, integration, and e2e validation.

## Runtime And Integration Boundaries

Runtime model:

1. FastAPI advisory service,
2. depends on `lotus-core` and `lotus-risk`,
3. consumed through `lotus-gateway` for integrated product flows.

Boundary rules:

1. advisor-only workflows belong here,
2. management-only workflows belong in `lotus-manage`,
3. proposal simulation must remain aligned with authoritative upstream data and risk posture,
4. runtime smoke should honor injected CI DSNs and canonical service identities rather than stale local assumptions.

## Repo-Native Commands

Use these commands as the primary local contract:

1. install
   `make install`
2. fast local gate
   `make check`
3. PR-grade local gate
   `make ci`
4. feature-lane local gate
   `make ci-local`
5. Docker parity
   `make ci-local-docker`
6. run locally
   `make run`

## Validation And CI Expectations

`lotus-advise` uses explicit CI lanes:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

Important validation expectations:

1. dependency health, OpenAPI, vocabulary, and no-alias governance are active,
2. migration smoke, coverage, Docker build, Postgres runtime smoke, and production-profile guardrail validation are part of the merge gate,
3. advisory workflow changes should be validated against canonical upstream posture.

## Standards And RFCs That Govern This Repository

Most relevant current governance:

1. `C:\Users\Sandeep\projects\lotus-platform\rfcs\RFC-0066-lotus-advise-to-lotus-advise-and-lotus-manage-split.md`
2. `C:\Users\Sandeep\projects\lotus-platform\rfcs\RFC-0067-centralized-api-vocabulary-inventory-and-openapi-documentation-governance.md`
3. `C:\Users\Sandeep\projects\lotus-platform\rfcs\RFC-0072-platform-wide-multi-lane-ci-validation-and-release-governance.md`
4. `C:\Users\Sandeep\projects\lotus-platform\rfcs\RFC-0073-lotus-ecosystem-engineering-context-and-agent-guidance-system.md`
5. `docs/standards/`

## Known Constraints And Implementation Notes

1. advisory and management boundaries must remain explicit after the repository split,
2. runtime smoke orchestration is operationally important here because CI includes real environment behavior, not just unit logic,
3. proposal behavior must not drift away from upstream data and risk authorities,
4. advisory lifecycle changes should update both code and repo context in the same slice.

## Context Maintenance Rule

Update this document when:

1. advisory workflow ownership or lifecycle scope changes,
2. repo-native commands or runtime smoke behavior changes,
3. upstream integration posture changes materially,
4. guardrail or production-profile expectations change,
5. current-state rollout posture changes.

## Cross-Links

1. `C:\Users\Sandeep\projects\lotus-platform\context\LOTUS-QUICKSTART-CONTEXT.md`
2. `C:\Users\Sandeep\projects\lotus-platform\context\LOTUS-ENGINEERING-CONTEXT.md`
3. `C:\Users\Sandeep\projects\lotus-platform\context\CONTEXT-REFERENCE-MAP.md`
4. `C:\Users\Sandeep\projects\lotus-platform\context\Repository-Engineering-Context-Contract.md`
