# Lotus Advise Quality Scorecard

- Branch: `advise-enterprise-hardening-slice-17`
- Head: `4f96f90fd9edd2736c0d5552bc9367f858c2819c`
- Progressive Gate Phase: `1 - baseline/report-only`

| Area | Status | Evidence |
| --- | --- | --- |
| Code size and hotspots | Baseline active | engineering-health + quality baseline |
| Complexity | Report-only gap | radon/xenon pending calibration |
| Maintainability | Improving | modularity slices and review ledger |
| Lint | Enforced | make lint |
| Type safety | Enforced | make typecheck |
| Coverage | Enforced | make coverage-combined fail-under 97 |
| Dead code | Report-only gap | vulture pending calibration |
| Dependencies | Enforced | dependency health check + pip-audit posture |
| Security | Partially enforced | security-audit plus pending bandit baseline |
| OpenAPI | Enforced plus report-only | openapi-gate + Spectral config |
| Architecture boundaries | Report-only gap | import-linter config added |
| Docs | Gap tracked | requested docs tracked in baseline report |
| Observability | Gap tracked | observability doc and diagnostics gates pending |
