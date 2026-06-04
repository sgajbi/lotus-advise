# Lotus Advise Refactor Health Report

- Branch: `advise-enterprise-hardening-slice-16`
- Head: `7484315d56c4a53a36773b205a0699f96101eb84`
- Branch Commits Over Main: `41`
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
- Proposal artifact assembly delegates portfolio, summary, trade/funding, review,
  evidence-bundle, and hash finalization to focused artifact modules.
- Advisory auto-funding planning delegates FX source selection and missing-rate
  diagnostics to a focused funding-selection module.
- Policy source-readiness assembly is split into Lotus Core, product-policy,
  and Lotus Risk source-owner section modules.
- Proposal memo foundational sections are split into focused per-section builders
  outside the shared memo section group coordinator.
- Proposal memo API orchestration delegates report-package and AI-evidence payloads
  to a focused external-package module.
- Proposal memo API response assembly delegates memo, audit-event, report replay,
  AI commentary, archive-ref, section, and replay-metadata projection to a
  focused response projection module.
- Proposal memo API external request orchestration delegates report-package and
  AI-commentary integration flows to a focused operations module.
- Alternative strategy construction delegates input DTOs, base mechanics,
  objective classes, selection helpers, trade-payload formatting, and notional math
  to focused strategy modules.
- Alternatives objective strategies are split into portfolio/cash, baseline-trade,
  currency-alignment, and deferred restricted-product modules.
- Advisor cockpit source read models delegate source projection helpers to a focused
  source-projection module while preserving the existing read-model facade.
- Advisor cockpit service delegates repository-backed source loading and tactical
  house-view source mapping to a focused source-loader module.
- Proposal workflow delivery operations delegate execution handoff, status, summary,
  history, and execution-update replay behavior to a focused service boundary.
- Proposal workflow narrative operations delegate narrative read/regeneration/review
  and report-request event recording to a focused service boundary.
- Proposal workflow read operations delegate proposal, timeline, approval, lineage,
  idempotency, version, and replay views to a focused service boundary.
- Engineering-health and quality-baseline reporting now provide repeatable evidence.

## Remaining Enterprise-Readiness Work

- Calibrate report-only tools: radon/xenon, vulture, deptry, bandit, import-linter,
  Spectral, interrogate, and optional schemathesis/load testing.
- Convert baseline reports into fail-on-new-regression gates before enforcing absolute
  thresholds.
- Continue moving oversized proposal/advisory service modules into focused use-case and
  policy modules with tests.
- Complete requested docs and wiki updates only when they describe implemented truth.
