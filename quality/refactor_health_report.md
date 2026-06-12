# Lotus Advise Refactor Health Report

- Branch: `harden/source-b-hotspots`
- Head: `508b42751ac874bbff75dd1e637ea955c2534c24`
- Branch Commits Over Main: `35`
- Current Phase: `feature-branch modularity and quality-baseline hardening`

## Current Progress Signals

- Proposal input models are split into focused context DTOs, request-envelope DTOs,
  and a compatibility facade.
- Proposal context resolution, canonical request hashing, and context evidence
  projection are split into focused owner modules with a compatibility facade.
- Advisory-copilot API DTOs are split into request, response, limits, and compatibility
  modules.
- Advisory-copilot source projections and run-record limits have focused owner modules.
- Advisory-copilot proposal-version lineage extraction delegates lineage-ref and
  section-source-ref matching to focused helpers.
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
- Target-generation solver orchestration delegates sell-only redistribution, solver
  indexing, constraint assembly, and solved-weight application to focused helpers.
- Proposal memo source-readiness assembly is split into core, risk, and Advise
  source-owner section groups.
- Proposal memo source-readiness owner groups are split into focused Lotus Core,
  Lotus Risk, and Lotus Advise modules with a compatibility facade.
- Bank-demo runtime summary sanitization is split into access helpers and
  focused projection builders.
- Bank-demo commercial material pack assembly delegates governed material rows to
  a focused catalog module.
- Bank-demo commercial material register validation delegates claim lookup,
  reference aggregation, and client-facing claim-posture checks to focused helpers.
- Bank-demo supported-claim classification validation delegates evidence,
  proof-reference, planned/unsupported, and UI-pending posture checks to focused helpers.
- Bank-demo proof-pack contract-reference normalization delegates scheme, credential,
  path, traversal, and sensitive-detail checks to focused helpers.
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
- Proposal memo foundational sections delegate summary extraction and value
  normalization to a focused helper module while preserving section construction.
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
- Proposal memo section assembly delegates source evidence and hash-payload
  collection to focused factory helpers.
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
- Policy evaluation source-readiness rule handling delegates policy-posture
  aggregation and section evidence collection to focused helpers.
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
- Proposal narrative grounding fact projection delegates decision-summary and
  alternatives fact assembly to focused helpers.
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
- Proposal workflow service async submission, execution, replay, correlation
  lookup, recovery, and test-stat facade methods live in a focused mixin.
- Proposal workflow service read, timeline, approval, lineage, version, replay,
  and idempotency lookup facade methods live in a focused read mixin.
- Advisory workspace routes are split into session/version, assistant-rationale,
  and lifecycle-handoff route modules behind the public aggregate router.
- Workspace draft action request validation delegates trade, cash-flow, options,
  and identifier-scope rules to focused helpers.
- Local valuation state assembly delegates position summary collection, cash
  conversion, shelf allocation, and allocation-metric rendering to focused helpers.
- Local position valuation delegates trust-snapshot authority handling,
  mark-to-market valuation, price lookup, and FX conversion to focused helpers.
- Enterprise write authorization delegates header normalization, required-header
  checks, service identity, capability config, and capability matching to
  focused helpers.
- In-memory proposal listing delegates filter matching, cursor slicing, and
  next-cursor calculation to focused query helpers.
- Persistent proposal listing delegates filter SQL, cursor SQL, query rendering,
  and page projection to focused helpers.
- OpenAPI operation enrichment delegates operation eligibility, default
  summary/description, tag inference, error response, and idempotency header handling.
- OpenAPI example repair delegates array, object-property, required-field,
  existing-field, and additional-property repair paths to focused helpers.
- OpenAPI example repair now delegates `$ref` and composite schema resolution,
  structured example dispatch, scalar enum/type checks, and integer bound checks.
- OpenAPI field-description inference delegates identifier, date/time, currency,
  monetary, quantity, rate/price, status, and fallback descriptions to focused helpers.
- OpenAPI example inference delegates const/enum/ref/composite priority handling
  and schema-type dispatch to focused helpers.
- OpenAPI string example inference delegates pattern, format, keyed, identifier,
  semantic-key, and fallback example paths to focused helpers.
- Commercial material source-reference normalization delegates text, repository-local
  location, path, and fragment validation to focused helpers.
- Bank-demo proof artifact-reference normalization delegates local text, URL/location,
  and path safety validation to focused helpers.
- Shared proposal intent dependency linking delegates SELL indexing, BUY selection,
  and idempotent dependency appending to focused helpers.
- API structured logging formatter delegates base payload, extra-field, audit-field,
  and null-filtering behavior to focused helpers.
- Policy-pack catalog state delegates validation/activation commands, audit-event
  mechanics, and detail projection to focused owner modules.
- Proposal decision-summary assembly delegates status, reason, next-action,
  and confidence rules to a focused decision-status module.
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
- Lotus Core stateful-context translation delegates payload normalization, market-data
  projection, and shelf-entry projection to focused owner modules.
- Lotus Core stateful-context source reads delegate enrichment cache partitioning,
  missing-id batching, source fetch, and cache writeback to focused helpers.
- Lotus Core stateful-context resolver and trade-draft hydration paths now read as
  orchestration over source fetch, validation, DTO assembly, and per-instrument
  hydration.
- Lotus Core liquidity-tier and simulation adapter logic delegates ordered policy
  rule evaluation, HTTP posting, problem-detail mapping, and contract validation.
- Proposal alternatives comparison summaries delegate approval/evidence count deltas
  and decimal risk/cash delta message projection to focused helpers.
- Proposal artifact and decision-summary rule helpers delegate next-step gate mapping,
  reason-code fallback, and approval-requirement collection to focused helpers.
- Proposal artifact trade projection and advisory auto-funding planning delegate
  execution DTO construction, dependency-note assembly, per-target funding,
  missing-FX handling, and FX-intent recording to focused helpers.
- Deterministic proposal narrative orchestration delegates section filtering,
  generation-mode handling, canonical narrative id construction, and status
  resolution to focused helpers.
- Proposal narrative executive-summary text delegates blocked, insufficient-evidence,
  and ready-for-review branches to focused renderers.
- Proposal narrative grounding facts delegate alternatives availability, selected
  alternative, count, rejected-summary, decision-scalar, approval, material-change,
  and missing-evidence projection to focused helpers.
- Proposal simulation security-trade intent planning delegates shelf presence,
  shelf eligibility, unsupported-trade diagnostics, and intent construction to
  focused helpers.
- Advisory copilot bounded tuple validation delegates sequence validation,
  bounded item normalization, duplicate handling, and non-empty enforcement to
  focused helpers.
- Advisory copilot structured payload validation delegates mapping, sequence,
  item-count, raw-AI key, and text safety checks to focused helpers.
- Advisory copilot run persistence delegates payload safety validation,
  idempotency replay lookup, run-record construction, retryable refresh, and
  idempotency-record construction to focused helpers.
- Enterprise readiness runtime policy delegates config issue collection,
  write-authorization denial selection, recursive audit redaction, and
  audit-identity validation to focused helpers while preserving bounded denial and
  redaction behavior.
- Integration dependency readiness delegates sanitized URL configuration,
  health-endpoint probing, readiness-basis selection, and unavailable-reason
  projection to focused helpers while preserving fail-closed dependency posture.
- Advisory supportability projection delegates dependency/feature counts,
  posture selection, degraded-state detection, and metric emission to focused
  helpers while preserving bounded supportability labels.
- Integration capability dependency diagnostics delegate readiness checks and
  public degraded-reason extraction to focused helpers while preserving
  fail-closed fallback behavior.
- API observability request-id normalization reuses the shared bounded
  identifier policy while preserving generated request-id fallback behavior.
- Proposal reporting service orchestration delegates related-version selection,
  reviewed-narrative packaging, request assembly, response normalization, and
  workflow recording to focused helpers.
- Policy-pack applicability evaluation delegates source context extraction,
  missing-evidence detection, not-applicable result construction, and selector
  construction to focused helpers.
- Engineering-health and quality-baseline reporting now provide repeatable evidence.

## Remaining Enterprise-Readiness Work

- Calibrate remaining report-only tools: xenon and optional schemathesis/load testing.
- Keep Spectral OpenAPI enforcement green while route and schema contracts evolve.
- Convert the Interrogate docstring inventory into a targeted documentation-quality gate
  after classifying public API and module ownership thresholds.
- Convert the Vulture dead-code inventory into a fail-on-new-regression gate after
  classifying validator and compatibility-facade findings.
- Expand Radon complexity enforcement beyond E/F-ranked blocks after classifying
  current high-complexity blocks.
- Expand Bandit security enforcement beyond high severity after classifying current
  SQL-construction findings and resolving true positives.
- Convert the deptry dependency inventory into a fail-on-new-regression gate after
  classifying current dependency findings.
- Convert baseline reports into fail-on-new-regression gates before enforcing absolute
  thresholds.
- Continue moving oversized proposal/advisory service modules into focused use-case and
  policy modules with tests.
- Complete requested docs and wiki updates only when they describe implemented truth.
