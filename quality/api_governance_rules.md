# Lotus Advise API Governance Rules

## Enforcement Phase

- Current phase: enforced repo-native OpenAPI gates plus continuing quality inventory.
- Existing enforcement: `make openapi-gate`, Spectral OpenAPI lint, API vocabulary inventory, and
  no-alias guard.

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

- `.spectral.yaml` defines enforced OpenAPI rules for operation IDs, descriptions, tags, and
  response documentation.
- `make openapi-spectral-report` exports the generated OpenAPI document and records the pinned
  Spectral inventory in `output/openapi-spectral-report.json`.
- `scripts/openapi_quality_gate.py` remains the repo-native OpenAPI gate.
- `quality/baseline_report.md` records Spectral executability, OpenAPI path count, issue count, and
  severity inventory.

## Next Gate

- Keep Spectral at zero findings and fail new OpenAPI lint regressions through `make openapi-gate`.
