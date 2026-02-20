# RFC-0022: DPM Policy Pack Configuration Model

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
| **Created** | 2026-02-20 |
| **Depends On** | RFC-0008, RFC-0010, RFC-0011, RFC-0016 |
| **Doc Location** | `docs/rfcs/RFC-0022-dpm-policy-pack-configuration-model.md` |

## 1. Executive Summary

Introduce a policy-pack configuration model so DPM rule behavior can be selected and tuned per business segment without code changes, similar to advisory configurability patterns.

## 2. Problem Statement

DPM currently relies on distributed flags and static defaults. As product variants grow, this makes onboarding and controlled rollout harder than necessary.

## 3. Goals and Non-Goals

### 3.1 Goals

- Centralize rule knobs into a policy-pack object.
- Allow per-request or per-tenant policy selection.
- Keep default behavior backward compatible.

### 3.2 Non-Goals

- Build tenant admin UI in this slice.
- Replace all configuration mechanisms at once.

## 4. Proposed Design

### 4.1 Policy Pack Shape

- `policy_pack_id`
- `version`
- `tax_policy`
- `turnover_policy`
- `settlement_policy`
- `constraint_policy`
- `workflow_policy`
- `idempotency_policy`

### 4.2 Resolution Strategy

- Order of precedence:
  - explicit request policy
  - tenant default policy
  - global engine default policy

### 4.3 Configurability

- `DPM_POLICY_PACKS_ENABLED` (default `false`)
- `DPM_DEFAULT_POLICY_PACK_ID`

## 5. Test Plan

- Policy resolution precedence tests.
- Backward-compatibility tests when feature is disabled.
- Rule behavior tests under two distinct policy packs.

## 6. Rollout/Compatibility

Feature-flagged rollout. Default path keeps current behavior with no client changes.

## 7. Status and Reason Code Conventions

Policy pack selection must not alter run status vocabulary semantics.

