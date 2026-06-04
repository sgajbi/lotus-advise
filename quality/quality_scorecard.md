# Lotus Advise Quality Scorecard

- Branch: `advise-enterprise-hardening-slice-17`
- Head: `c1003aecee39b9186e7bb8c47846d80dd7d5613b`
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
