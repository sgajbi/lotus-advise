# Enterprise Readiness Baseline (lotus-advise)

- Standard reference: `lotus-platform/Enterprise Readiness Standard.md`
- Scope: advisory workflow APIs, proposal lifecycle operations, and integration-aware readiness controls.
- Change control: RFC for platform-level changes, ADR for temporary exceptions.

## Security and IAM Baseline

- Enterprise audit middleware captures privileged state transitions.
- Actor/tenant/role/correlation metadata is logged with sensitive-value redaction.

Evidence:
- `src/api/enterprise_readiness.py`
- `src/api/main.py`
- `tests/unit/advisory/api/test_api_internal_guards.py`

## API Governance Baseline

- API contracts are versioned and documented through OpenAPI.
- Backward compatibility and deprecation are governed by RFC process.

Evidence:
- `src/api/main.py`
- `tests/unit/advisory/contracts`
- `tests/integration`

## Configuration and Feature Management Baseline

- Feature controls are configured via `ENTERPRISE_FEATURE_FLAGS_JSON`.
- Tenant/role fallback resolution is deterministic and deny-by-default.

Evidence:
- `src/api/enterprise_readiness.py`
- `tests/unit/advisory/api/test_api_internal_guards.py`

## Data Quality and Reconciliation Baseline

- Portfolio/input validation and decision constraints are enforced in domain services.
- Reconciliation and durability rules are documented under dedicated standards.

Evidence:
- `docs/standards/durability-consistency.md`
- `tests/unit/advisory/engine`

## Reliability and Operations Baseline

- Health/readiness, retry/timeout controls, migration gating, and supportability runbooks are enforced.
- `GET /platform/capabilities` publishes `advise.observability.advisory_supportability`
  plus a source-backed `supportability` summary for Gateway and Workbench consumers.
- `/metrics` emits `lotus_advise_advisory_supportability_total` with bounded `state`,
  `reason`, and `freshness_bucket` labels only; it must not include portfolio, client, request,
  response, correlation, or trace identifiers as labels.

Evidence:
- `src/api/main.py`
- `src/api/observability.py`
- `src/api/routers/integration_capabilities.py`
- `docs/standards/scalability-availability.md`
- `docs/standards/migration-contract.md`

## Privacy and Compliance Baseline

- Audit-trail integrity includes actor context and redacted metadata for sensitive values.

Evidence:
- `src/api/enterprise_readiness.py`
- `tests/unit/advisory/api/test_api_internal_guards.py`

## Deviations

- Deviations require ADR with mitigation and expiry review date.

