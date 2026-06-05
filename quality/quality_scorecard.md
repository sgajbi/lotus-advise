# Lotus Advise Quality Scorecard

- Branch: `harden/quality-gate-calibration`
- Head: `110cc35dc02ca5a527c3166b4169bcc0a66fc0c2`
- Progressive Gate Phase: `1 - baseline/report-only`

| Area | Status | Evidence |
| --- | --- | --- |
| Code size and hotspots | Baseline active | engineering-health + quality baseline |
| Complexity | No-E/F gate plus Radon inventory | complexity-regression-gate + radon rank and worst-complexity counts |
| Maintainability | Improving | modularity slices and review ledger |
| Lint | Enforced | make lint |
| Type safety | Enforced | make typecheck |
| Coverage | Enforced | make coverage-combined fail-under 97 |
| Dead code | Executable Vulture inventory | vulture issue and confidence counts |
| Dependencies | Enforced plus deptry inventory | dependency health check + pip-audit posture + deptry issue count |
| Security | High-severity enforced plus Bandit inventory | security-audit + bandit-high-severity-gate + Bandit severity counts |
| OpenAPI | Enforced with Spectral | openapi-gate + Spectral zero-finding inventory |
| Architecture boundaries | Enforced | make lint runs import-linter architecture contracts |
| Docs | Gap tracked plus Interrogate inventory | requested docs + docstring coverage inventory |
| Observability | Diagnostics target added | make observability-diagnostics |
