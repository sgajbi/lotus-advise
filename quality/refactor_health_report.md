# Lotus Advise Refactor Health Report

- Branch: `harden/proposal-context-boundaries`
- Head: `360ad1cb36584ec29b91d3d99a040a47a9fb0b76`
- Branch Commits Over Main: `41`
- Current Phase: `feature-branch modularity and quality-baseline hardening`

## Current Progress Signals

- Proposal input models are split into focused context DTOs, request-envelope DTOs,
  and a compatibility facade.
- Proposal context resolution, canonical request hashing, and context evidence
  projection are split into focused owner modules with a compatibility facade.
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
- Proposal memo source-readiness owner groups are split into focused Lotus Core,
  Lotus Risk, and Lotus Advise modules with a compatibility facade.
- Bank-demo runtime summary sanitization is split into access helpers and
  focused projection builders.
- Bank-demo commercial material pack assembly delegates governed material rows to
  a focused catalog module.
- Bank-demo journey integration proof DTOs and validators are split into a focused
  model owner while preserving the proof summary builder and public import path.
- Proposal artifact assembly delegates portfolio, summary, trade/funding, review,
  evidence-bundle, and hash finalization to focused artifact modules.
- Advisory auto-funding planning delegates FX source selection and missing-rate
  diagnostics to a focused funding-selection module.
- Policy source-readiness assembly is split into Lotus Core, product-policy,
  and Lotus Risk source-owner section modules.
- Proposal memo foundational sections are split into focused per-section builders
  outside the shared memo section group coordinator.
- Proposal memo evidence-pack assembly delegates deterministic section, appendix,
  and material-claim construction to a focused section factory.
- Proposal memo API orchestration delegates report-package and AI-evidence payloads
  to a focused external-package module.
- Proposal memo API routes are split into command, external-package, and read/projection
  route modules while preserving the route loader and OpenAPI surface.
- Policy evaluation API routes are split into command, read/projection, workflow,
  and external-package route modules while preserving the route loader and OpenAPI
  surface.
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
- Proposal alternatives models are split into vocabulary, request-validation,
  response/evidence, and compatibility facade modules.
- Proposal alternatives projection delegates request-to-strategy input mapping
  to a focused projection module.
- Proposal alternatives comparison evidence delegates approval, risk, cash,
  currency, and tradeoff deltas to a focused projection module.
- Proposal alternatives ranking delegates comparator, reason-code, rank,
  and selected-alternative projection to a focused ranking module.
- Proposal memo request DTOs and memo vocabulary literals are split from
  response, lineage, and replay evidence models.
- Proposal memo persistence records are split into a focused owner module
  while preserving the existing persistence model facade.
- Proposal memo audit event DTOs are split into a focused append-only
  event model module.
- Proposal memo lineage and replay evidence DTOs are split into a
  focused lineage response module.
- Policy evaluation result builders are split from specialized rule
  evaluation logic.
- Policy evaluation product evidence helpers are split from specialized
  rule evaluation logic.
- Policy evaluation Singapore product rule implementations are split
  into a focused rule-family module.
- Policy evaluation cost and conflict review rules are split into a
  focused review-rule module.
- Policy evaluation source-readiness and mandate rules are split into
  a focused source-rule module.
- Proposal artifact summary DTOs are split into a focused summary model module
  while preserving the existing artifact model facade.
- Proposal artifact portfolio-impact DTOs are split into a focused portfolio model
  module while preserving the existing artifact model facade.
- Proposal artifact trade/funding DTOs are split into a focused execution-evidence
  model module while preserving the existing artifact model facade.
- Proposal artifact review DTOs are split into a focused suitability/risk-lens
  model module while preserving the existing artifact model facade.
- Proposal artifact assumptions and disclosure DTOs are split into a focused
  model module while preserving the existing artifact model facade.
- Proposal artifact evidence DTOs are split into a focused lineage/evidence
  model module while preserving the existing artifact model facade.
- Proposal artifact builders import focused DTO owner modules directly instead of
  routing section DTOs through the artifact model facade.
- Proposal narrative vocabulary Literal aliases are split into a focused type
  module while preserving the existing narrative model facade.
- Proposal narrative request DTOs are split into a focused request model module
  while preserving the existing narrative model facade.
- Proposal narrative grounding DTOs are split into a focused evidence model module
  while preserving the existing narrative model facade.
- Proposal narrative section DTOs are split into a focused section model module
  while preserving the existing narrative model facade.
- Proposal narrative policy and guardrail DTOs are split into a focused policy
  model module while preserving the existing narrative model facade.
- Proposal narrative AI-lineage DTOs are split into a focused AI model module
  while preserving the existing narrative model facade.
- Proposal narrative envelope DTOs are split into a focused envelope model module
  while preserving the existing narrative model facade.
- Proposal narrative review DTOs are split into a focused review model module
  while preserving the existing narrative model facade.
- Proposal narrative runtime modules import focused DTO owner modules directly
  instead of routing DTOs through the narrative model facade.
- Advisor cockpit source read models delegate source projection helpers to a focused
  source-projection module while preserving the existing read-model facade.
- Advisor cockpit source projection delegates policy-review and memo package blockage
  source rules to a focused policy/memo projection module.
- Advisor cockpit source projection delegates proposal meeting-preparation, client
  follow-up, and approval-dependency rules to a focused proposal projection module.
- Advisor cockpit source projection delegates report/archive readiness and execution
  handoff/status rules to focused source-family projection modules.
- Advisor cockpit service delegates repository-backed source loading and tactical
  house-view source mapping to a focused source-loader module.
- In-memory proposal repository adapters delegate pure filtering, ordering,
  batching, recoverable-operation selection, and copy semantics to focused helpers.
- Advisor cockpit service delegates acknowledgement idempotency, replay,
  persistence payload, and response projection to a focused service boundary.
- Engine option models delegate suitability threshold DTOs, group constraints,
  and reusable validators to focused owner modules while preserving public imports.
- Tactical house-view source products delegate DTOs and eligibility/supportability
  rules to focused owner modules while preserving the public cohort facade.
- Policy evaluation workflow commands delegate projection and sign-off decision
  validation to focused workflow owner modules.
- Integration capability response models delegate feature/workflow, readiness,
  and supportability DTO families to focused owner modules while preserving
  the public response facade.
- Proposal workflow service construction delegates operation-owner wiring to
  a focused registry while preserving the public service facade.
- Advisory workspace routes are split into session/version, assistant-rationale,
  and lifecycle-handoff route modules behind the public aggregate router.
- Policy-pack catalog state delegates validation/activation commands, audit-event
  mechanics, and detail projection to focused owner modules.
- Proposal workflow delivery operations delegate execution handoff, status, summary,
  history, and execution-update replay behavior to a focused service boundary.
- Proposal workflow narrative operations delegate narrative read/regeneration/review
  and report-request event recording to a focused service boundary.
- Proposal workflow read operations delegate proposal, timeline, approval, lineage,
  idempotency, version, and replay views to a focused service boundary.
- Proposal workflow command operations delegate create, version, transition, and
  approval commands to a focused service boundary.
- Policy evaluation persistence delegates lineage/posture projection and audit-event
  attachment mapping to a focused projection module.
- Policy evaluation persistence delegates replay hash comparison and replay response
  assembly to a focused replay module.
- Policy evaluation persistence delegates mutable record storage, idempotency replay,
  event construction, and store-backed projections to a focused record-store module.
- Engineering-health and quality-baseline reporting now provide repeatable evidence.

## Remaining Enterprise-Readiness Work

- Calibrate report-only tools: radon/xenon, vulture, deptry, bandit, import-linter,
  Spectral, interrogate, and optional schemathesis/load testing.
- Convert baseline reports into fail-on-new-regression gates before enforcing absolute
  thresholds.
- Continue moving oversized proposal/advisory service modules into focused use-case and
  policy modules with tests.
- Complete requested docs and wiki updates only when they describe implemented truth.
