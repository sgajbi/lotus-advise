# Lotus Advise Quality Scorecard

- Branch: `harden/quality-gate-calibration`
- Head: `aa87bf51e0b5a4223607fbbb1b4a0a2213b4d618`
- Progressive Gate Phase: `1 - baseline/report-only`

| Area | Status | Evidence |
| --- | --- | --- |
| Code size and hotspots | Baseline active | engineering-health + quality baseline |
| Complexity | Executable Radon inventory | radon rank and worst-complexity counts |
| Maintainability | Improving | modularity slices and review ledger |
| Lint | Enforced | make lint |
| Type safety | Enforced | make typecheck |
| Coverage | Enforced | make coverage-combined fail-under 97 |
| Dead code | Executable Vulture inventory | vulture issue and confidence counts |
| Dependencies | Enforced plus deptry inventory | dependency health check + pip-audit posture + deptry issue count |
| Security | Partially enforced plus Bandit inventory | security-audit + Bandit severity counts |
| OpenAPI | Enforced plus report-only | openapi-gate + Spectral config |
| Architecture boundaries | Executable report-only contracts | import-linter kept/broken contract inventory |
| Docs | Gap tracked | requested docs tracked in baseline report |
| Observability | Gap tracked | observability doc and diagnostics gates pending |
