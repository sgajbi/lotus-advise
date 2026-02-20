# RFC-0021: DPM OpenAPI Contract Hardening and Separation of Request/Response Models

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
| **Created** | 2026-02-20 |
| **Depends On** | RFC-0007A, RFC-0016, RFC-0017 |
| **Doc Location** | `docs/rfcs/RFC-0021-dpm-openapi-contract-hardening.md` |

## 1. Executive Summary

Harden DPM OpenAPI contracts so request and response objects are explicitly separated, with complete field-level descriptions/examples and contract tests to prevent accidental schema drift.

## 2. Problem Statement

Schema ambiguity and mixed request/response models reduce integrator confidence and make production support harder. Advisory APIs already use stricter schema discipline.

## 3. Goals and Non-Goals

### 3.1 Goals

- Separate request and response models for public endpoints.
- Require field descriptions and examples for Swagger quality.
- Add contract tests that assert schema shape and metadata.

### 3.2 Non-Goals

- Re-architect core engine logic.
- Introduce breaking route changes.

## 4. Proposed Design

### 4.1 OpenAPI Improvements

- Dedicated DTOs for request vs response per endpoint.
- `Field(..., description=..., examples=[...])` coverage for each public attribute.
- Consistent error envelope docs.

### 4.2 Contract Testing

- Snapshot/semantic tests over `/openapi.json`.
- Assertions for required fields, enums, and examples on targeted models.

### 4.3 Configurability

- `DPM_STRICT_OPENAPI_VALIDATION` (default `true` in CI, configurable locally)

## 5. Test Plan

- OpenAPI generation test for each DPM route family.
- Schema tests for required example/description coverage.
- Regression tests for idempotency and supportability models.

## 6. Rollout/Compatibility

No runtime behavior change intended. External clients benefit from clearer contracts and stronger backward compatibility guardrails.

## 7. Status and Reason Code Conventions

No status vocabulary changes introduced by this RFC.

