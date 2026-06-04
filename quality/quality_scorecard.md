# Lotus Advise Quality Scorecard

- Branch: `harden/quality-gate-calibration`
- Head: `357de2e2e9cbebdb4ce944c292a80e5b667e5904`
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
| Docs | Gap tracked plus Interrogate inventory | requested docs + docstring coverage inventory |
| Observability | Diagnostics target added | make observability-diagnostics |
