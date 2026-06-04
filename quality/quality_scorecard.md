# Lotus Advise Quality Scorecard

- Branch: `harden/quality-gate-calibration`
- Head: `0518f315bf8c6653cad2a6428c84e9fc50ab416d`
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
| Dependencies | Enforced plus deptry inventory | dependency health check + pip-audit posture + deptry issue count |
| Security | Partially enforced | security-audit plus pending bandit baseline |
| OpenAPI | Enforced plus report-only | openapi-gate + Spectral config |
| Architecture boundaries | Report-only gap | import-linter config added |
| Docs | Gap tracked | requested docs tracked in baseline report |
| Observability | Gap tracked | observability doc and diagnostics gates pending |
