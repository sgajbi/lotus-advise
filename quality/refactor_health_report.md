# Lotus Advise Refactor Health Report

- Branch: `advise-enterprise-hardening-slice-15`
- Head: `2270f04b41c1f8780a4a0c511c1a5492dc39ee15`
- Branch Commits Over Main: `25`
- Current Phase: `feature-branch modularity and quality-baseline hardening`

## Current Progress Signals

- Advisory-copilot API DTOs are split into request, response, limits, and compatibility
  modules.
- Advisory-copilot source projections and run-record limits have focused owner modules.
- Advisory simulation orchestration is split into intent planning, review policy,
  and decision-support modules with focused boundary tests.
- Feature capability catalog assembly is split into foundation, evidence-product,
  and operational capability groups.
- Workflow capability catalog assembly is split into foundation, evidence-product,
  and operational workflow groups.
- Proposal memo section assembly is split into foundational, policy-review,
  operational, and appendix section groups.
- Bank-demo supported-claim register assembly is split into artifact policy,
  backend-evidence, product-surface, and boundary claim groups.
- Compliance rule evaluation is split into focused cash-band, concentration,
  data-quality, trade-size, shorting, and cash-sufficiency evaluators.
- Proposal memo source-readiness assembly is split into core, risk, and Advise
  source-owner section groups.
- Bank-demo runtime summary sanitization is split into access helpers and
  focused projection builders.
- Bank-demo commercial material pack assembly delegates governed material rows to
  a focused catalog module.
- Proposal artifact assembly delegates portfolio, summary, trade/funding, and review
  projections to focused artifact modules.
- Advisory auto-funding planning delegates FX source selection and missing-rate
  diagnostics to a focused funding-selection module.
- Engineering-health and quality-baseline reporting now provide repeatable evidence.

## Remaining Enterprise-Readiness Work

- Calibrate report-only tools: radon/xenon, vulture, deptry, bandit, import-linter,
  Spectral, interrogate, and optional schemathesis/load testing.
- Convert baseline reports into fail-on-new-regression gates before enforcing absolute
  thresholds.
- Continue moving oversized proposal/advisory service modules into focused use-case and
  policy modules with tests.
- Complete requested docs and wiki updates only when they describe implemented truth.
