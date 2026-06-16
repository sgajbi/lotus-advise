# Lotus Advise Quality Scorecard

- Git Identity: omitted from committed Markdown; use Git history and GitHub Actions
  run metadata for exact branch/head evidence.
- Progressive Gate Phase: `1 - baseline/report-only`

| Area | Status | Evidence |
| --- | --- | --- |
| Code size and hotspots | Baseline active | engineering-health + quality baseline |
| Complexity | No-C/D/E/F gate plus Radon inventory | complexity-regression-gate + radon rank and worst-complexity counts |
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

## Before/After Evidence

- Before baseline: `origin/main` report head
  `f6a82186ed52e3eb3568ae0de2bbb2919f18f90d`.
- After baseline: current generated report content is enforced by
  `make quality-baseline-check`; exact head evidence belongs to Git history
  and GitHub Actions run metadata.

| Area | Before | After | Improvement Evidence |
| --- | --- | --- | --- |
| Complexity | Radon and Xenon tracked as pending report-only tools. | Radon config executable; inventory `A=3668, B=130`; worst block `B/8`; no C/D/E/F gate enforced through `make lint`. | Complexity is now measured repeatably and regression-blocked for C-ranked and worse blocks. |
| Maintainability | Review ledger existed but recent proposal, policy-pack, OpenAPI, proof-material, dependency-linking, and observability slices were absent. | Review ledger includes `LA-REV-611` through `LA-REV-831` with scoped findings, evidence, and follow-up. | Modularization and hotspot reductions are traceable by owner boundary and test evidence. |
| OpenAPI quality | Spectral rules were present but report-only until Node/Spectral execution was added to CI. | Spectral config executable; OpenAPI path inventory `84`; current Spectral issue inventory `0`; enforced through `make openapi-gate`. | OpenAPI quality moved from report-only posture to enforced zero-finding gate. |
| Architecture boundaries | Import-linter contracts were present but report-only pending installation and baseline. | Import-linter inventory `total=3, kept=3, broken=0`; architecture contracts run inside `make lint`. | Layering contracts are now executable and locally enforced. |
| Tests | Unit suite existed; new focused refactor regressions were absent. | Repo-native test gates are enforced through `make check`; focused regression tests cover OpenAPI enrichment, proof refs, source refs, dependency linking, capability dependency diagnostics, observability request-id normalization, structured logging, target-generation solver index construction, target-generation solver fallback policy, runtime base URL safety, Lotus Core route-resolution policy, advisory copilot idempotency replay, classification boundaries, Lotus Risk issuer mapping, Lotus Report request mapping, Lotus Core held-position selection, Lotus Core dated-row selection, proposal narrative product-type policy, advisory copilot review/source-projection persistence, advisory copilot section tuple validation, suitability issue projection, and CI warning/topology contracts. | Refactors are covered by behavior-preserving regression tests. |
| Security | Bandit config was present for report-only rollout; sensitive-data handling remained test-governed. | Bandit inventory executable with `high=0, medium=26, low=1`; high-severity gate enforced through `make security-audit`; proof/source refs reject unsafe and sensitive paths. | Security posture is measured and high-severity findings are gated. |
| Dependency hygiene | Dependency audit configured; deptry inventory absent from the scorecard. | Deptry config executable with current inventory `14`; dependency/security tools inventory recorded. | Dependency hygiene moved from broad audit posture to measurable inventory. |
| Observability | Observability docs and diagnostics were tracked as baseline gaps. | `make observability-diagnostics` target exists; structured formatter has direct tests for context, extra fields, audit fields, and null filtering. | Observability behavior is documented, testable, and less complex. |
| Documentation | Requested docs were present; docstring inventory was not calibrated. | Requested docs remain present; Interrogate inventory executable at `0.8%`; scorecard, baseline, and refactor-health reports are generated. | Documentation gaps are explicitly inventoried and tied to generated quality reports. |

## Known Limits

- This scorecard proves measurable engineering improvement; it does not claim bank
  certification, regulatory approval, client-ready publication, or production
  deployment approval.
- Xenon strict thresholds, Vulture fail-on-new-regression, Deptry
  fail-on-new-regression, medium/low Bandit classification, and public API
  docstring thresholds remain governed follow-up work.
