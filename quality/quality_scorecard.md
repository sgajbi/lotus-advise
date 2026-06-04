# Lotus Advise Quality Scorecard

- Branch: `harden/quality-gate-calibration`
- Head: `8f366239677720ed391a788fb50e087f227705d6`
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
| Architecture boundaries | Enforced | make lint runs import-linter architecture contracts |
| Docs | Gap tracked | requested docs tracked in baseline report |
| Observability | Gap tracked | observability doc and diagnostics gates pending |
