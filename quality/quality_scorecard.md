# Lotus Advise Quality Scorecard

- Branch: `harden/quality-gate-calibration`
- Head: `4b24a14b2d2b22c311bd2b02671f2ed5a50bc636`
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
| Security | Partially enforced plus Bandit inventory | security-audit + Bandit severity counts |
| OpenAPI | Enforced plus report-only | openapi-gate + Spectral config |
| Architecture boundaries | Report-only gap | import-linter config added |
| Docs | Gap tracked | requested docs tracked in baseline report |
| Observability | Gap tracked | observability doc and diagnostics gates pending |
