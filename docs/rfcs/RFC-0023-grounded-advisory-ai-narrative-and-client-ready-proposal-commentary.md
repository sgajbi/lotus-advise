# RFC-0023: Grounded Advisory AI Narrative and Client-Ready Proposal Commentary

- Status: DRAFT
- Created: 2026-04-12
- Owners: lotus-advise
- Requires Approval From: lotus-advise, lotus-ai, lotus-core, lotus-risk, lotus-manage maintainers
- Depends On: RFC-0006, RFC-0011, RFC-0013, RFC-0014, RFC-0015, RFC-0019, RFC-0020, RFC-0021, RFC-0022
- Related Platform Guidance: `lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
- Related Platform Governance: `lotus-platform/rfcs/RFC-0072-platform-wide-multi-lane-ci-validation-and-release-governance.md`

## Executive Summary

`lotus-advise` should support high-quality advisory narrative, but AI must not become the source of investment truth. In a banking-grade platform, generative AI can help draft advisor and client commentary only when it is grounded in deterministic, auditable backend evidence.

This RFC defines an in-place enhancement to existing advisory proposal, artifact, and workspace surfaces that introduces a grounded advisory narrative layer. The layer produces controlled commentary for advisor review, compliance review, and client-ready proposal artifacts. It consumes evidence from canonical proposal simulation, risk lenses, suitability policy, decision summary, alternatives comparison, lifecycle state, and approved disclosure templates.

The target outcome is not generic AI text generation. The target is governed narrative composition with:

1. strict evidence grounding,
2. deterministic input packets,
3. approved vocabulary and tone controls,
4. citation/evidence references,
5. suitability and risk caveats,
6. jurisdiction-aware disclosures,
7. human approval workflow,
8. full persistence and replay.

Because `lotus-advise` is not live and all callers are controlled, this RFC enhances existing APIs in place. It does not introduce public `/v2` APIs.

## Why This RFC Exists

A private banker needs to explain proposals clearly and consistently. Current proposal evidence can support strong advisory decisions, but raw data is not enough for enterprise-grade client communication.

A real advisory platform should help produce:

1. advisor-facing summary of the recommendation,
2. client-friendly investment rationale,
3. risk and suitability explanation,
4. before/after portfolio impact commentary,
5. alternatives comparison narrative,
6. approval and remediation explanation,
7. jurisdiction-aware disclosures,
8. artifact-ready commentary that can be reviewed and approved.

Without a governed narrative layer, future UI or artifact work may create superficial AI features that sound polished but are not anchored to backend evidence. That is unacceptable in a private-banking, compliance-sensitive platform.

This RFC makes AI useful while keeping deterministic backend evidence authoritative.

## Current State

### What Is Already Strong

Current and planned proposal capabilities provide:

1. canonical simulation evidence through `lotus-core`,
2. risk lens evidence through `lotus-risk`,
3. persisted proposal lifecycle and audit evidence,
4. proposal artifacts,
5. workspace save and handoff,
6. RFC-0021 decision summary and enterprise suitability policy,
7. RFC-0022 alternatives and comparison evidence.

### What Is Not Yet Business Grade

The system does not yet provide:

1. governed proposal narrative generation,
2. evidence-grounded commentary packets,
3. approved narrative sections and templates,
4. citation mapping from text to evidence refs,
5. hallucination and unsupported-claim controls,
6. jurisdiction-aware disclosure insertion,
7. narrative review workflow,
8. stable persisted narrative versions,
9. AI observability and quality checks.

## Problem Statement

`lotus-advise` needs a narrative layer that improves advisor productivity without compromising auditability, suitability, compliance, or domain correctness.

The platform must ensure that narrative output:

1. never invents portfolio facts,
2. never hides blockers or approval requirements,
3. never converts insufficient evidence into a positive suitability claim,
4. never presents unapproved text as final client advice,
5. uses private-banking vocabulary correctly,
6. includes evidence references for material claims,
7. can be replayed exactly for audit,
8. can be regenerated only under explicit versioned inputs and policy.

AI can draft language. It must not own suitability, risk, allocation, AUM, recommendation readiness, approval requirements, or product eligibility.

## Requirement Traceability

| Requirement | RFC Section | Acceptance Evidence Required |
| --- | --- | --- |
| AI must be grounded in deterministic evidence | Grounding Packet Model, Architecture Direction | Tests prove narrative inputs are built only from allowed evidence refs |
| AI must not own advisory decisions | Domain Authority Boundaries | Tests prove decision status, suitability, risk, and approvals come from backend evidence |
| Unsupported claims must be prevented | Unsupported Claim Guardrails | Guardrail tests reject claims without evidence refs |
| Narrative must be reviewable and replayable | Persistence and Replay, Review Workflow | Persistence tests prove exact narrative version replay and approval state |
| Jurisdiction disclosure must be controlled | Disclosure and Jurisdiction Policy | Tests prove required disclosures are selected by policy, not model invention |
| UI must not generate client-ready text locally | API and UI Alignment | Contract exposes backend-generated narrative sections and review metadata |
| Final documentation and agent guidance must be assessed | Slice 8 | Final slice evidence records context updates or explicit no-change decision |

## Goals

1. Add governed advisory narrative support to existing proposal surfaces.
2. Define deterministic grounding packets from proposal evidence.
3. Support advisor-facing, compliance-facing, and client-ready narrative sections.
4. Use approved templates, tone controls, vocabulary, and disclosure policy.
5. Require evidence refs for material claims.
6. Persist narrative versions with proposal versions and artifacts.
7. Support human review, approval, rejection, and regeneration workflow.
8. Integrate with `lotus-ai` or an AI provider through a narrow, auditable adapter.
9. Make narrative output safe for future UI and artifact consumption.
10. Preserve strict domain authority boundaries.

## Non-Goals

1. Do not introduce public `/v2` route families.
2. Do not allow AI to calculate portfolio, allocation, AUM, performance, or risk metrics.
3. Do not allow AI to determine suitability, approval requirements, or recommendation status.
4. Do not allow AI to generate trades or alternatives.
5. Do not ship fully automated client communication without human approval.
6. Do not allow free-form prompt surfaces in production proposal flows.
7. Do not make `lotus-advise` a general-purpose chat application.
8. Do not bypass jurisdiction, product, suitability, or disclosure policy.

## Pre-Live Contract Hardening Decision

Because the app is not live, this RFC enhances existing contracts in place.

Allowed changes:

1. additive narrative fields on proposal, artifact, workspace, and replay responses,
2. internal narrative policy, template, grounding, and guardrail versions,
3. optional read-only endpoints under existing `/advisory/proposals/...` route family,
4. controlled adapter integration with `lotus-ai` or a governed model provider,
5. persisted narrative version metadata.

Disallowed changes:

1. public `/v2` APIs,
2. unmanaged prompt endpoints,
3. UI-only generation of client-ready text,
4. narrative fields not backed by proposal evidence,
5. hidden model calls during persisted replay.

## Domain Authority Boundaries

### lotus-core

`lotus-core` remains authoritative for:

1. portfolio state,
2. positions,
3. cash,
4. AUM,
5. allocation,
6. valuation,
7. market/reference data,
8. simulation.

Narrative may describe these facts only when they exist in grounding evidence.

### lotus-risk

`lotus-risk` remains authoritative for:

1. risk analytics,
2. concentration lens,
3. future risk methodologies,
4. risk lineage.

Narrative may explain risk evidence but must not create risk metrics or imply unavailable risk evidence passed.

### lotus-manage or Client/Mandate Authority

Client profile, mandate, booking center, restrictions, and preferences must come from canonical client/mandate sources when available.

Narrative must not claim client suitability or mandate fit when that evidence is missing.

### lotus-ai

`lotus-ai` or the selected AI provider owns:

1. model execution,
2. prompt orchestration primitives if centralized there,
3. model telemetry where applicable,
4. shared AI safety infrastructure where applicable.

`lotus-ai` does not own advisory truth. It receives a constrained grounding packet and returns draft narrative for validation.

### lotus-advise

`lotus-advise` owns:

1. narrative use case definition,
2. proposal grounding packet construction,
3. allowed narrative sections,
4. disclosure and tone policy selection,
5. unsupported-claim validation,
6. narrative review lifecycle,
7. persistence and replay of narrative evidence,
8. artifact and UI projection.

## Target Capability

The target capability introduces `proposal_narrative` evidence composed of:

1. grounding packet,
2. narrative request policy,
3. generated narrative sections,
4. claim-to-evidence map,
5. disclosure set,
6. guardrail results,
7. review state,
8. artifact projection metadata.

The narrative layer must support non-AI deterministic template fallback where AI is unavailable or disabled.

## Target API Contract

### Additive Request Fields

Existing proposal artifact/workspace/create/version flows may include optional narrative settings:

```json
{
  "narrative_request": {
    "enabled": true,
    "audience": "ADVISOR_REVIEW",
    "sections": ["EXECUTIVE_SUMMARY", "PORTFOLIO_IMPACT", "RISK_AND_SUITABILITY", "ALTERNATIVES_COMPARISON"],
    "tone": "PRIVATE_BANKING_CONCISE",
    "language": "en",
    "jurisdiction": "SG",
    "require_human_approval": true
  }
}
```

### Additive Response Fields

Add `proposal_narrative` where narrative is generated or persisted:

1. proposal artifact response,
2. proposal create/version response when narrative is requested,
3. workspace save/handoff response,
4. proposal detail/version detail,
5. async replay after success,
6. artifact replay.

### Optional Projection Endpoints

Add read-only or workflow endpoints only under existing advisory route family if needed:

1. `GET /advisory/proposals/{proposal_id}/versions/{version_id}/narrative`
2. `POST /advisory/proposals/{proposal_id}/versions/{version_id}/narrative/review`

Replay endpoints must return persisted narrative and must not silently call AI again.

## Narrative Audience Vocabulary

Allowed audiences:

1. `ADVISOR_REVIEW`,
2. `COMPLIANCE_REVIEW`,
3. `CLIENT_DRAFT`,
4. `CLIENT_READY`.

`CLIENT_READY` requires explicit approval workflow and disclosure checks.

## Narrative Section Vocabulary

Allowed initial sections:

1. `EXECUTIVE_SUMMARY`,
2. `RECOMMENDATION_RATIONALE`,
3. `PORTFOLIO_IMPACT`,
4. `RISK_AND_SUITABILITY`,
5. `MATERIAL_CHANGES`,
6. `ALTERNATIVES_COMPARISON`,
7. `APPROVALS_AND_ACTIONS`,
8. `KEY_RISKS`,
9. `DISCLOSURES`,
10. `NEXT_STEPS`.

Sections must be backed by explicit evidence availability. If evidence is missing, the section must either omit the claim or state the limitation clearly according to policy.

## ProposalNarrative Model

Suggested model shape:

```json
{
  "narrative_id": "nar_001",
  "narrative_policy_version": "advisory-narrative-policy.2026-04",
  "grounding_packet_version": "proposal-grounding.2026-04",
  "generation_mode": "AI_ASSISTED",
  "audience": "ADVISOR_REVIEW",
  "language": "en",
  "tone": "PRIVATE_BANKING_CONCISE",
  "status": "DRAFT_REQUIRES_REVIEW",
  "sections": [],
  "claim_evidence_map": [],
  "disclosures": [],
  "guardrail_results": [],
  "review_state": {},
  "evidence_refs": []
}
```

Generation modes:

1. `DETERMINISTIC_TEMPLATE`,
2. `AI_ASSISTED`,
3. `AI_UNAVAILABLE_TEMPLATE_FALLBACK`.

Narrative statuses:

1. `DRAFT_REQUIRES_REVIEW`,
2. `APPROVED_FOR_ADVISOR_USE`,
3. `APPROVED_FOR_CLIENT_USE`,
4. `REJECTED_UNSUPPORTED_CLAIMS`,
5. `REJECTED_POLICY_VIOLATION`,
6. `REQUIRES_REGENERATION`,
7. `INSUFFICIENT_EVIDENCE`.

## Grounding Packet Model

The grounding packet is the only allowed input to narrative generation.

Required contents:

1. proposal identity and version,
2. as-of date and portfolio identity,
3. advisor-requested intents,
4. before/after state summary,
5. allocation deltas from `lotus-core`,
6. risk lens from `lotus-risk`,
7. decision summary from RFC-0021,
8. alternatives comparison from RFC-0022 where available,
9. suitability posture and missing evidence,
10. approval requirements,
11. material changes,
12. data-quality posture,
13. jurisdiction and disclosure policy,
14. allowed vocabulary and prohibited claims,
15. evidence refs for every material fact.

The grounding packet must not include unrestricted raw internal data if it is not needed for the narrative.

## Narrative Section Model

Each section should include:

1. `section_id`,
2. `section_type`,
3. `title`,
4. `body`,
5. `audience`,
6. `status`,
7. `required_review`,
8. `claims`,
9. `evidence_refs`,
10. `disclosure_refs`,
11. `policy_warnings`.

Claims should be structured where possible so guardrails can validate them.

## Claim Evidence Model

Each material claim should map to evidence.

Suggested fields:

1. `claim_id`,
2. `claim_type`,
3. `text_span_ref`,
4. `evidence_refs`,
5. `confidence`,
6. `validation_status`,
7. `failure_reason_code`.

Claim types:

1. `PORTFOLIO_FACT`,
2. `ALLOCATION_CHANGE`,
3. `RISK_FACT`,
4. `SUITABILITY_FACT`,
5. `APPROVAL_REQUIREMENT`,
6. `ALTERNATIVE_COMPARISON`,
7. `DISCLOSURE`,
8. `LIMITATION_OR_MISSING_EVIDENCE`.

## Unsupported Claim Guardrails

Narrative output must be rejected or downgraded when it contains:

1. unsupported return expectations,
2. unsupported risk reduction claims,
3. suitability pass claims without evidence,
4. client-specific claims without client context,
5. undisclosed product complexity,
6. missing approval requirements,
7. promises or guarantees,
8. performance predictions not backed by approved methodology,
9. facts not present in the grounding packet,
10. prohibited jurisdictional language.

Guardrails must produce stable reason codes and remediation guidance.

## Disclosure and Jurisdiction Policy

Disclosures must be selected by deterministic policy.

Inputs:

1. jurisdiction,
2. booking center,
3. product types,
4. risk posture,
5. suitability posture,
6. client audience,
7. execution boundary,
8. data-quality limitations,
9. AI-assisted generation indicator where required by policy.

The model must not invent disclosures. It may only select, assemble, or phrase approved disclosure content according to policy.

## Architecture Direction

### Grounding Packet Builder

Builds a deterministic input object from persisted proposal evidence.

Rules:

1. no model calls,
2. no free-form evidence scraping,
3. no local recalculation of portfolio or risk metrics,
4. stable ordering of evidence,
5. explicit missing evidence.

### Narrative Policy Resolver

Selects allowed sections, audience, tone, disclosures, prohibited claims, and review requirements.

Rules:

1. policy version must be explicit,
2. jurisdiction behavior must be deterministic,
3. client-ready output must require review workflow,
4. unavailable policy must block client-ready narrative.

### AI Adapter

Calls `lotus-ai` or the governed provider through a narrow interface.

Rules:

1. accepts only grounding packet plus approved generation instructions,
2. no direct database access,
3. no unmanaged prompt input from UI,
4. timeout and fallback behavior required,
5. model and prompt/template versions captured.

### Narrative Validator

Validates output before persistence or projection.

Rules:

1. every material claim must map to evidence,
2. prohibited claims fail validation,
3. missing disclosures fail client-ready validation,
4. unsupported claims produce actionable reason codes,
5. failed validation does not return as approved narrative.

### Review Workflow

Manages approval state for advisor and client use.

Rules:

1. generated narrative starts as draft,
2. client-ready narrative requires explicit approval,
3. review action is auditable,
4. rejected narrative preserves rejection reason,
5. regeneration creates a new narrative version.

## Persistence and Replay

Required behavior:

1. grounding packet is persisted or reproducibly referenced,
2. narrative output is persisted with proposal version,
3. model/prompt/template/policy versions are persisted,
4. guardrail results are persisted,
5. review state is persisted,
6. replay returns exact narrative evidence,
7. replay does not call AI again,
8. regeneration creates a new narrative version linked to source evidence.

## Degraded Behavior

Narrative must degrade safely.

Examples:

1. AI unavailable falls back to deterministic template if policy allows,
2. missing decision summary blocks advisory narrative generation,
3. missing risk evidence prevents risk improvement claims,
4. missing client context prevents personalized suitability claims,
5. missing disclosure policy blocks client-ready narrative,
6. guardrail failure returns rejected narrative evidence, not polished unsafe text.

## API and UI Alignment

UI must consume backend narrative sections and review state.

UI may allow:

1. selecting audience,
2. selecting allowed sections,
3. requesting generation,
4. reviewing and approving drafts,
5. showing claim evidence drill-down,
6. inserting approved narrative into artifacts.

UI must not:

1. call a model directly for proposal narrative,
2. generate client-ready text locally,
3. hide guardrail failures,
4. remove required disclosures,
5. edit evidence-backed facts without creating a reviewable override,
6. present AI draft as approved advice.

## Delivery Slices

### Slice 1: Current-State Assessment and Narrative Contract Baseline

Outcome:

1. map current artifact, proposal detail, workspace, lifecycle, replay, and UI narrative needs,
2. identify deterministic evidence available from RFC-0021 and RFC-0022,
3. define additive narrative request/response contract,
4. define allowed audiences, sections, statuses, and review states,
5. prove no public API v2 is required.

Acceptance gate:

1. assessment document exists with code/test evidence,
2. narrative contract is reconciled with API vocabulary governance,
3. first implementation scope is explicit,
4. no implementation begins until evidence ownership and review workflow are clear.

### Slice 2: Grounding Packet and Deterministic Template Baseline

Outcome:

1. implement grounding packet builder over persisted proposal evidence,
2. implement deterministic template fallback for advisor review,
3. add narrative models without AI dependency,
4. expose narrative output in artifact path where requested.

Acceptance gate:

1. unit tests prove grounding packet contains only allowed evidence,
2. missing evidence is explicit,
3. deterministic template produces stable output,
4. no model calls are needed for baseline narrative.

### Slice 3: Narrative Policy, Disclosures, and Guardrail Framework

Outcome:

1. add narrative policy resolver,
2. add approved disclosure selection,
3. add unsupported-claim validation framework,
4. add client-ready blocking behavior when policy or disclosure is incomplete.

Acceptance gate:

1. disclosure tests cover jurisdiction, product type, risk posture, and client audience,
2. guardrail tests reject unsupported claims,
3. missing disclosure policy blocks client-ready narrative,
4. policy versions are persisted.

### Slice 4: lotus-ai Adapter and AI-Assisted Draft Generation

Outcome:

1. integrate through a narrow AI adapter,
2. send only grounding packet and approved instructions,
3. capture model/prompt/template versions,
4. support timeout and deterministic fallback,
5. validate AI output before persistence.

Acceptance gate:

1. adapter tests prove no raw unmanaged prompt is accepted,
2. timeout tests prove safe fallback or failure,
3. validation rejects unsupported AI claims,
4. AI-assisted output remains draft until review.

### Slice 5: Review Workflow, Persistence, Artifact, and Replay

Outcome:

1. persist narrative versions with proposal versions,
2. add review actions for approve/reject/regenerate where needed,
3. include approved narrative in artifacts,
4. preserve narrative through workspace handoff,
5. replay exact narrative evidence.

Acceptance gate:

1. persistence tests prove exact narrative replay,
2. review tests prove client-ready status requires approval,
3. artifact tests prove only approved client-ready narrative is included,
4. regeneration tests prove new narrative version lineage.

### Slice 6: Alternatives and Decision Summary Narrative Integration

Outcome:

1. generate sections from RFC-0021 decision summary,
2. generate alternatives comparison commentary from RFC-0022 evidence,
3. include approval/action explanation,
4. include material changes and risk/suitability limitations.

Acceptance gate:

1. blocked proposal narrative highlights blockers before benefits,
2. insufficient evidence narrative does not imply suitability pass,
3. alternatives narrative explains tradeoffs using backend comparison evidence,
4. approval requirements are not omitted.

### Slice 7: Live Validation and Operator Evidence

Outcome:

1. extend live validation to request deterministic and AI-assisted narrative where enabled,
2. validate advisor-review and client-draft flows,
3. validate AI-unavailable fallback,
4. emit evidence for generation mode, guardrail status, review state, and latency.

Acceptance gate:

1. live suite validates deterministic narrative without AI dependency,
2. AI-assisted mode is validated where credentials/runtime are available,
3. unavailable AI does not break proposal core flow,
4. guardrail failure path is observable and reproducible.

### Slice 8: Documentation, Agent Context, and Branch Hygiene

Outcome:

1. update RFC status and index when implemented,
2. update API docs, artifact docs, narrative policy docs, and operator runbooks,
3. update `REPOSITORY-ENGINEERING-CONTEXT.md` if grounded narrative patterns become durable guidance,
4. update platform or agent context if future agents need reusable AI-safety guidance,
5. assess whether skill guidance should change,
6. complete PR loop, merge, delete local and remote feature branches, and sync `main`.

Acceptance gate:

1. docs clearly distinguish deterministic evidence from AI-assisted draft text,
2. context/skill changes are either made or explicitly assessed as no-change-needed,
3. RFC index is current,
4. required GitHub checks are green,
5. branch hygiene leaves `local = remote = main` after merge.

Skill/context assessment requirement:

1. Determine whether Lotus agent guidance should add a grounded-AI advisory narrative pattern.
2. Determine whether a reusable skill/playbook is needed for AI-backed financial narrative features.
3. Determine whether context should explicitly prohibit AI-owned suitability, risk, or recommendation decisions.
4. Record a no-change rationale if no context or skill update is needed.

## Test Strategy

Required test layers:

1. grounding packet builder tests,
2. narrative model and OpenAPI tests,
3. deterministic template tests,
4. policy resolver tests,
5. disclosure selection tests,
6. unsupported-claim guardrail tests,
7. AI adapter contract tests,
8. timeout/fallback tests,
9. review workflow tests,
10. persistence and replay tests,
11. artifact tests,
12. workspace handoff tests,
13. degraded dependency tests,
14. live validation tests.

High-value scenarios:

1. advisor-review narrative for ready proposal,
2. blocked proposal narrative that leads with remediation,
3. insufficient-evidence narrative with explicit limitations,
4. risk-review proposal with clear risk caveats,
5. alternatives comparison narrative with evidence refs,
6. client-ready narrative blocked by missing approval,
7. unsupported AI claim rejected by guardrails,
8. AI unavailable and deterministic fallback used,
9. replay returns exact persisted narrative,
10. regeneration creates new version lineage.

Tests must validate business behavior and safety controls. Snapshot-only text tests are not sufficient unless paired with structured evidence assertions.

## Performance and Scalability Expectations

Narrative generation must not slow the core proposal path by default.

Required behavior:

1. narrative generation is opt-in initially,
2. deterministic template generation is fast and local,
3. AI calls have strict timeout and retry policy,
4. proposal core simulation must remain usable if AI is unavailable,
5. grounding packets are bounded and avoid unnecessary raw payloads,
6. repeated generation uses idempotency and version lineage,
7. large artifacts do not trigger unbounded model context growth.

Latency goals:

1. deterministic narrative should add negligible latency,
2. AI-assisted narrative should be asynchronous or clearly timed where needed,
3. live validation should record generation and validation latency,
4. timeout behavior must be predictable and observable.

## Observability and Operations

Add structured observability for:

1. narrative generation requested,
2. generation mode,
3. audience,
4. section count,
5. grounding packet version,
6. policy/template/model versions,
7. guardrail pass/fail counts,
8. unsupported claim reason codes,
9. disclosure selection counts,
10. review state transitions,
11. AI latency and timeout counts,
12. fallback usage.

Readiness/capabilities should expose:

1. narrative capability enabled,
2. deterministic template readiness,
3. AI adapter readiness,
4. disclosure policy readiness,
5. supported audiences,
6. supported sections,
7. client-ready narrative readiness.

## Documentation Requirements

Update or add:

1. RFC implementation evidence,
2. API docs for narrative request/response,
3. grounding packet guide,
4. narrative policy and disclosure guide,
5. AI adapter runbook,
6. artifact narrative guide,
7. review workflow guide,
8. live validation guide,
9. repository engineering context if new patterns emerge,
10. agent operating guidance if new repeatable workflows emerge.

## Naming and Vocabulary Rules

Use private-banking advisory language and avoid generic AI product wording.

Preferred terms:

1. `proposal_narrative`, not `ai_text`,
2. `grounding_packet`, not `prompt_data`,
3. `claim_evidence_map`, not `citations` alone,
4. `disclosures`, not `legal_text`,
5. `review_state`, not `approval_flag`,
6. `generation_mode`, not `ai_mode`,
7. `unsupported_claims`, not `hallucinations` in API contracts,
8. `client_ready`, not `final_text`.

Reason codes must be stable upper snake case.

Narrative language must reflect private banking, portfolio analytics, suitability, risk, mandate, product, and advisory-domain vocabulary.

## Rollout and Compatibility

1. The RFC is additive and pre-live.
2. Existing proposal APIs are enhanced in place.
3. Narrative is opt-in at first.
4. Deterministic template support should ship before AI-assisted generation.
5. Client-ready narrative remains disabled until policy, disclosure, review, and guardrail controls are validated.
6. UI adoption must follow backend contract availability.
7. Post-live breaking changes require a dedicated versioning RFC.

## Open Questions Before Implementation

These must be resolved in Slice 1:

1. Should the first implementation support advisor-review only, or advisor-review plus client-draft?
2. Which `lotus-ai` adapter contract is canonical for proposal narrative?
3. Which jurisdictions and disclosure packs are supported initially?
4. Which narrative sections are required by the first UI/artifact flow?
5. What human approval model is required before client-ready artifact export?
6. What model/provider telemetry is required for audit?
7. Which prompt/template/version artifacts belong in `lotus-advise` versus `lotus-ai`?

## Risks and Mitigations

### Risk: AI invents advisory facts

Mitigation:

1. use grounding packet only,
2. validate claim evidence mapping,
3. reject unsupported claims,
4. keep deterministic backend evidence authoritative.

### Risk: AI output is mistaken for approved advice

Mitigation:

1. default generated text to draft status,
2. require review workflow for client-ready use,
3. expose review state clearly in API and UI,
4. block artifact inclusion unless approved by policy.

### Risk: Disclosures become inconsistent

Mitigation:

1. select disclosures by deterministic policy,
2. version disclosure packs,
3. test jurisdiction and product combinations,
4. prohibit model-invented disclosures.

### Risk: Narrative slows proposal workflow

Mitigation:

1. make narrative opt-in,
2. support deterministic fallback,
3. use async generation where needed,
4. enforce AI timeout and observability.

### Risk: UI adds unmanaged prompt features

Mitigation:

1. expose governed narrative endpoints,
2. document UI restrictions,
3. reject unmanaged prompt surfaces during review,
4. add contract tests for backend-owned narrative fields.

## Completion Criteria

This RFC is implemented when:

1. proposal narrative can be requested through existing advisory surfaces,
2. deterministic grounding packets are built from allowed proposal evidence,
3. deterministic template fallback works without AI dependency,
4. AI-assisted draft generation uses a narrow governed adapter where enabled,
5. unsupported claims and missing disclosures are blocked by guardrails,
6. narrative versions persist and replay exactly,
7. client-ready output requires explicit review and approval,
8. artifacts include only allowed narrative sections,
9. live validation proves ready, blocked, insufficient-evidence, fallback, and guardrail paths,
10. documentation, agent context assessment, and branch hygiene are completed in the final slice.
