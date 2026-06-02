# Lotus Advise API Governance Rules

## Enforcement Phase

- Current phase: baseline/report-only plus existing repo-native OpenAPI gates.
- Existing enforcement: `make openapi-gate`, API vocabulary inventory, and no-alias guard.

## Endpoint Rules

- Every endpoint should have a summary, description, tags, operation ID, request model where
  applicable, response model, examples where useful, and standard error responses.
- Pagination, filtering, sorting, versioning, deprecation, and supportability boundaries should be
  consistent across proposal and advisory surfaces.
- Downstream and domain errors should map to consistent platform error details.
- RFC 7807/problem-details adoption is a future governed migration unless already implemented by a
  specific endpoint family.
- Every externally relevant request should support or propagate a correlation ID.
- Relevant mutations must define auditability, lineage, and idempotency behavior.

## Current Evidence

- `.spectral.yaml` defines report-only OpenAPI rules for operation IDs, descriptions, tags, and
  response documentation.
- `scripts/openapi_quality_gate.py` remains the repo-native OpenAPI gate.
- `quality/baseline_report.md` records Spectral execution as report-only pending Node/Spectral CI
  installation.

## Next Gate

- Add Spectral execution as report-only CI.
- Capture OpenAPI warning inventory.
- Move to fail-on-new-regression after the warning inventory is stable.
