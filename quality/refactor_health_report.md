# Lotus Advise Refactor Health Report

- Branch: `advise-enterprise-hardening-slice-15`
- Head: `a96debc2054115accf66aa87abbcd03370f23423`
- Branch Commits Over Main: `11`
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
- Engineering-health and quality-baseline reporting now provide repeatable evidence.

## Remaining Enterprise-Readiness Work

- Calibrate report-only tools: radon/xenon, vulture, deptry, bandit, import-linter,
  Spectral, interrogate, and optional schemathesis/load testing.
- Convert baseline reports into fail-on-new-regression gates before enforcing absolute
  thresholds.
- Continue moving oversized proposal/advisory service modules into focused use-case and
  policy modules with tests.
- Complete requested docs and wiki updates only when they describe implemented truth.
