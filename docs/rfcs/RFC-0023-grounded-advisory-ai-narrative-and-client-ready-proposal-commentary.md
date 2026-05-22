# RFC-0023: Grounded Advisory AI Narrative and Client-Ready Proposal Commentary

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT - GOLD-STANDARD IMPLEMENTATION PLAN |
| **Created** | 2026-04-12 |
| **Last Tightened** | 2026-05-22 |
| **Slice 0 Closure** | Implemented on 2026-05-22 in `docs/rfcs/RFC-0023-slice-0-critical-review-source-map-and-product-gap-allocation.md`; this is source-map and scope-gate proof only, not proposal narrative capability |
| **Owner** | `lotus-advise` for proposal narrative authority, grounding packets, review lifecycle, persistence, replay, and advisory API truth |
| **Business Sponsor Persona** | relationship manager, investment advisor, compliance reviewer, investment desk reviewer, operations support, audit, client-reporting owner, sales/pre-sales |
| **Primary Business Outcome** | make advisory recommendation commentary explainable, evidence-grounded, review-gated, replayable, artifact-ready, and safe for client-facing proposal workflows |
| **Requires Approval From** | `lotus-advise`, `lotus-ai`, `lotus-core`, `lotus-risk`, `lotus-report`, `lotus-render`, `lotus-archive`, `lotus-gateway`, `lotus-workbench`, `lotus-platform`, and `lotus-manage` maintainers where handoff proof is required |
| **Depends On** | RFC-0006, RFC-0011, RFC-0013, RFC-0014, RFC-0015, RFC-0019, RFC-0020, RFC-0021, RFC-0022 |
| **Cross-Repository Scope** | `lotus-advise`, `lotus-ai`, `lotus-core`, `lotus-risk`, `lotus-report`, `lotus-render`, `lotus-archive`, `lotus-gateway`, `lotus-workbench`, `lotus-platform`, and `lotus-manage` only where advisory-to-DPM handoff proof is required |
| **Compatibility Posture** | backward compatibility is not a constraint while the app remains pre-live; breaking API/contract cleanup is allowed when it is cleaner, but all affected downstream consumers must be migrated in this RFC before closure |
| **Tightening Branch** | `docs/rfc0023-gold-standard-tightening` |
| **Implementation Branching Rule** | use one remote feature branch for RFC-0023 or one coherent implementation slice; all branch names, PRs, commits, checks, evidence paths, and closure state must be recorded in RFC closure evidence |
| **Related Platform Guidance** | `lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md` |
| **Related Platform Governance** | `lotus-platform/rfcs/RFC-0072-platform-wide-multi-lane-ci-validation-and-release-governance.md` |
| **Doc Location** | `docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md` |

---

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

This RFC is now the single execution source for grounded advisory narrative. New WTBD records must
not be created for this work. If implementation discovers upstream, downstream, platform, UI,
report, archive, AI, security, documentation, data-product, or operational work needed to support
the narrative claim, that work must be added to this RFC as a slice, owner-repository PR, acceptance
criterion, explicit blocked state, or removed claim.

This RFC cannot close as "backend done, UI later," "AI prompt done, guardrails later," or
"documentation later." Client-ready commentary is a banking-grade product claim and must be backed
by source authority, review workflow, audit, replay, lineage, OpenAPI, Gateway/Workbench consumption,
report/render/archive realization where client artifacts are claimed, and mainline CI evidence.

## Critical Review of the Previous RFC

| Area | Previous state | Gap | Tightening applied |
| --- | --- | --- | --- |
| Scope | Focused on grounded proposal narrative inside `lotus-advise`. | Downstream report, archive, Gateway, Workbench, supportability, data-product, and platform proof were not hard gates. | Added full cross-repo ownership, product-surface proof, report/archive realization, platform automation, and closure requirements. |
| Compatibility | Correctly avoided public `/v2` APIs because the service is pre-live. | Did not state whether breaking cleanup is allowed. | Compatibility is explicit: clean breaking changes are allowed, but all affected consumers must be migrated in the same RFC. |
| AI authority | Correctly said AI must not own investment truth. | Needed stronger source-authority language across suitability, risk, alternatives, approval, disclosure, and execution posture. | Added source-authority rules, data-product posture, unsupported-claim controls, and AI non-authority acceptance gates. |
| Business outcome | Explained why narrative matters. | Did not define bank-buyable outcomes for advisor productivity, compliance confidence, client conversation quality, audit, and commercial proof. | Added explicit business outcomes and documentation-as-product expectations. |
| Product gap handling | Listed narrative capability and open questions. | Did not allocate overlap with RFC-0024, RFC-0025, RFC-0026, RFC-0027, RFC-0028, report stack, or Workbench. | Added product-gap allocation and cross-RFC integration rules. |
| Data mesh | Mentioned evidence refs. | Did not require producer/consumer declarations, trust telemetry, SLO/access/evidence policy, mesh certification, or safe evidence-pack posture where a data-product claim is made. | Added data-mesh and trust-telemetry requirements for any promoted narrative evidence product. |
| API certification | Proposed additive request/response fields and endpoints. | Did not require Swagger quality, field descriptions, examples, error responses, API vocabulary, no-alias checks, or endpoint certification. | Added certified API and OpenAPI gates. |
| Testing | Had a broad test strategy. | Needed stronger live/canonical, report/archive, Gateway/Workbench, degraded-source, guardrail, replay, idempotency, and security evidence. | Expanded slices and acceptance gates to cover all material proof paths. |
| Final closure | Had documentation and branch-hygiene language. | Did not explicitly require wiki publication, Main Releasability Gate, stranded-truth reconciliation, supported-features promotion rules, or post-completion communication posture. | Added final closure, wiki, branch hygiene, and implementation-backed communication rules. |

Decision:

1. RFC-0023 remains the owning RFC for grounded advisory narrative and client-ready proposal
   commentary.
2. RFC-0023 must deliver the narrative-critical subset end to end before downstream RFCs may claim
   supported client-ready narrative behavior.
3. Adjacent RFCs may consume or extend RFC-0023, but no adjacent RFC may close by relying on
   unimplemented narrative truth outside this RFC.

## Business Outcomes

RFC-0023 must deliver these outcomes:

1. **Advisor productivity**
   advisors receive structured commentary drafts from source-backed proposal evidence rather than
   hand-writing explanations from raw endpoint responses.
2. **Compliance confidence**
   suitability, risk, approvals, disclosures, unsupported claims, missing evidence, model lineage,
   and human-review state are visible and auditable.
3. **Client conversation quality**
   client-draft and client-ready commentary use clear private-banking language while preserving
   review gates and evidence references.
4. **Audit and replay**
   narrative versions, grounding packets, guardrail results, review actions, policy versions, and
   model/template lineage can be replayed exactly.
5. **Operational resilience**
   AI unavailable, missing policy, missing disclosure, insufficient evidence, and guardrail failure
   degrade safely without blocking core proposal workflows.
6. **Product-surface truth**
   Gateway, Workbench, report, render, and archive surfaces expose only implementation-backed
   narrative states and never infer narrative facts locally.
7. **Commercial readiness**
   wiki, demo, and sales/pre-sales wording distinguish supported narrative behavior from planned
   roadmap without implying unsupported AI or regulatory capability.

## Product Gap Allocation

| Product area or gap | RFC-0023 treatment | Owning RFC or repo for broader scope |
| --- | --- | --- |
| Grounded proposal narrative | In scope as the core capability. | `lotus-advise` owns narrative use case and lifecycle. |
| AI model execution | In scope only through bounded workflow-pack or provider adapter calls. | `lotus-ai` owns shared AI execution primitives and model telemetry. |
| Advisor proposal memo sections | In scope where narrative feeds memo sections. | RFC-0024 owns the full memo evidence product. |
| Suitability, best-interest, fees, conflicts, and disclosure packs | In scope only for narrative-critical source-backed input and blockers. | RFC-0025 owns full enterprise policy packs; RFC-0016 owns broader costs/frictions. |
| Advisor cockpit workflow | In scope only where narrative review actions must surface. | RFC-0026 owns full cockpit operating workflow. |
| Broader AI copilot | Out of scope except for shared narrative lineage and safety controls. | RFC-0027 owns broad copilot interaction. |
| Bank demo and client-ready proof | In scope for narrative proof consumed by demo journey. | RFC-0028 owns complete bank demo journey and RFP/client-ready packaging. |
| Report/render/archive client artifacts | In scope when client-ready narrative is included in generated artifacts. | `lotus-report`, `lotus-render`, and `lotus-archive` own document lifecycle. |
| Gateway and Workbench consumption | In scope for any supported UI or experience API claim. | `lotus-gateway` and `lotus-workbench` own product delivery boundaries. |
| Advisory/DPM handoff commentary | In scope only where narrative explains advisory-to-execution boundary evidence. | `lotus-manage` owns DPM campaigns, action registers, and execution supportability. |
| Platform automation and governance | In scope when reusable gaps are discovered. | `lotus-platform` owns scaffolding, validators, standards, mesh certification, and canonical proof automation. |

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
| Report/render/archive client artifacts must stay source-backed | Product Gap Allocation, Delivery Slices | Cross-repo tests prove client-ready narrative enters artifacts only after review and policy gates |
| Gateway and Workbench must consume backend-owned narrative | API and UI Alignment, Delivery Slices | Gateway contract and browser tests prove no local UI narrative generation or unsupported inference |
| Data-product and supportability claims must be implementation-backed | Data Mesh, Trust, and Supportability Baseline | Domain-product, trust telemetry, capability, SLO/access/evidence, and mesh proof exist before promotion |
| Final documentation and agent guidance must be assessed | Final Closure Slice | Final slice evidence records README/wiki/context/skill updates or explicit no-change decision |

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

## Source Authority and Dependency Map

Narrative output must never be treated as an originating source. It is a projection over source
evidence.

| Evidence family | Source authority | RFC-0023 consumption rule |
| --- | --- | --- |
| Portfolio identity, holdings, cash, AUM, valuation, allocation, simulation | `lotus-core` | Consume source refs and source-readiness posture; do not recalculate or infer missing portfolio facts. |
| Risk, concentration, drawdown, stress, risk-lineage posture | `lotus-risk` | Explain only provided metrics and degraded states; missing risk evidence blocks risk-improvement claims. |
| Proposal lifecycle, proposal version, artifact, workspace, approval posture | `lotus-advise` | Persist narrative against exact proposal version and lifecycle evidence; replay must not call AI again. |
| Decision summary and recommendation readiness | `lotus-advise` RFC-0021 implementation | Use as source for recommended action and blockers; AI cannot promote readiness. |
| Alternatives comparison | `lotus-advise` RFC-0022 implementation | Use backend alternatives evidence and rejected-alternative reason codes; AI cannot invent alternatives. |
| Suitability, best-interest, jurisdiction, policy, disclosure, fee/cost/conflict posture | `lotus-advise` and policy/source owners; RFC-0025/RFC-0015/RFC-0016 where implemented | Use implemented policy evidence or explicit blocked/missing posture; never convert absence into positive language. |
| Model execution, prompt/workflow-pack lineage, model telemetry | `lotus-ai` or governed provider adapter | Receive bounded grounding packets only; return draft text plus lineage for validation. |
| Report, render, archive, retention, access audit | `lotus-report`, `lotus-render`, `lotus-archive` | Client-ready artifacts require review-approved narrative and returned report/archive lineage refs. |
| Experience API and product surface | `lotus-gateway`, `lotus-workbench` | Consume canonical Advise narrative APIs through Gateway/BFF only; no UI-owned client-ready generation. |
| Advisory-to-DPM handoff state | `lotus-advise` for advisory posture; `lotus-manage` for DPM system-of-record truth | Narrative may explain boundary evidence only when source handoff status and ownership are explicit. |

## Data Mesh, Trust, and Supportability Baseline

If RFC-0023 promotes a narrative evidence product or exposes narrative as supported product truth,
the implementation must satisfy the current Lotus data-product and supportability baseline:

1. add or update repo-native domain-product declarations only for implementation-backed narrative
   products,
2. emit trust telemetry for the supported narrative product or record a deliberate blocked posture
   until runtime telemetry exists,
3. define SLO, access, and evidence policy posture where platform certification requires it,
4. update `/platform/capabilities` only after deterministic narrative, policy, guardrail, review,
   replay, and dependency readiness are real,
5. preserve bounded metric labels and safe operator diagnostics without proposal text, client names,
   portfolio identifiers, raw prompts, raw responses, trace IDs, or correlation IDs as metric labels,
6. run the repo-native domain-product gate and relevant platform mesh certification when product
   declarations or trust evidence change,
7. publish only audience-filtered evidence packs; public or sales-demo material must not expose raw
   grounding packets, restricted telemetry paths, prompts, model outputs, entitlement details, or
   client-identifying data.

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

Each slice must produce a small, meaningful commit or coordinated cross-repo PR set. Required
upstream, downstream, UI, report, archive, platform, documentation, data-product, and security work
must be added to these slices rather than parked in WTBD or a side ledger.

### Slice 0: Critical Review, Source Map, and Product Gap Allocation

Status: implemented as source-map and scope-gate proof in
`docs/rfcs/RFC-0023-slice-0-critical-review-source-map-and-product-gap-allocation.md`. This status
does not promote proposal narrative as a supported capability.

Outcome:

1. complete the pre-implementation source map for proposal, artifact, workspace, decision summary,
   alternatives, suitability/policy, risk, disclosures, AI, report, archive, Gateway, Workbench,
   DPM handoff, data product, trust telemetry, and supportability evidence,
2. classify RFC-0023 overlap with RFC-0024 through RFC-0028,
3. decide which narrative-critical dependencies must be implemented now, blocked explicitly, or
   removed from supported claims.

Acceptance gate:

1. every material narrative claim has a source authority or blocked-state owner,
2. required cross-repo work is represented as an RFC-0023 slice, owner-repository PR, or explicit
   blocked/removed supported claim,
3. no broad "later", WTBD, or side-branch truth remains for the narrative supported claim.

### Slice 1: Platform Automation and Scaffolding Improvement

Outcome:

1. identify repeatable gaps that should be solved in `lotus-platform` rather than locally,
2. improve platform automation or scaffolding when gaps are found.

Required review areas:

1. API certification and Swagger/OpenAPI quality,
2. bounded observability, safe diagnostics, health, liveness, readiness, and capabilities posture,
3. structured logging, correlation, error handling, and problem-details defaults,
4. AI workflow-pack safety and evidence scaffolding,
5. data-product declarations, trust telemetry, SLO/access/evidence policy, and mesh certification,
6. live-evidence capture and canonical front-office proof patterns,
7. README/wiki/documentation scaffolding and governance hooks.

Acceptance gate:

1. reusable platform improvements are implemented in `lotus-platform` or explicitly rejected with
   rationale,
2. platform changes have platform-native tests and PR evidence,
3. RFC-0023 does not create one-off local patterns where a reusable standard is required.

### Slice 2: Cleanup and Structure

Outcome:

1. clean advisory narrative-adjacent module boundaries before adding capability,
2. remove stale docs, duplicate target-state language, misleading AI claims, and obsolete prompt or
   artifact conventions,
3. establish clear domain, policy, grounding, validation, persistence, AI-adapter, report-handoff,
   API, supportability, and projection boundaries.

Acceptance gate:

1. controllers remain thin and narrative business logic is not embedded in API facades or UI helper
   code,
2. dead code and duplicate documentation discovered in the slice are removed or explicitly
   retained with rationale,
3. repo docs are layered rather than duplicated.

### Slice 3: Current-State Assessment and Narrative Contract Baseline

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

### Slice 4: Data Product and Supportability Baseline

Outcome:

1. define whether RFC-0023 promotes a narrative evidence product,
2. implement domain-product declarations, trust telemetry, SLO/access/evidence policy, and
   supportability posture only when implementation-backed,
3. expose `/platform/capabilities` narrative support only after deterministic readiness exists.

Acceptance gate:

1. repo-native domain-product gate passes when declarations change,
2. trust telemetry and mesh certification pass where a product claim is made,
3. capabilities and supported-features material do not overclaim AI-assisted or client-ready
   readiness.

### Slice 5: Grounding Packet and Deterministic Template Baseline

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

### Slice 6: Narrative Policy, Disclosures, and Guardrail Framework

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

### Slice 7: lotus-ai Adapter and AI-Assisted Draft Generation

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

### Slice 8: Review Workflow, Persistence, Idempotency, Artifact, and Replay

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
4. regeneration tests prove new narrative version lineage,
5. duplicate generation or review requests are idempotent where the API contract requires it.

### Slice 9: Alternatives, Decision Summary, and Policy Evidence Integration

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

### Slice 10: Certified APIs and OpenAPI

Outcome:

1. expose canonical narrative request/read/review/regeneration/lineage/replay endpoints or additive
   fields under the existing advisory route family,
2. update OpenAPI, vocabulary, no-alias, examples, error responses, field descriptions, and header
   guidance,
3. migrate affected consumers in the same RFC.

Acceptance gate:

1. OpenAPI quality, API vocabulary, and no-alias gates pass,
2. endpoint certification covers behavior and every material returned field,
3. stale or duplicate narrative route shapes are removed or explicitly deprecated.

### Slice 11: Report, Render, Archive, Gateway, and Workbench Realization

Outcome:

1. include review-approved narrative in report/render/archive flows where client artifacts are
   claimed,
2. expose narrative review, guardrail, disclosure, lineage, and artifact posture through Gateway and
   Workbench,
3. preserve advisory-to-DPM boundary evidence where narrative references execution handoff.

Acceptance gate:

1. `lotus-gateway` consumes canonical `lotus-advise` narrative endpoints,
2. Workbench consumes Gateway/BFF only and does not infer narrative facts locally,
3. report/render/archive references are source-backed and blocked when review posture is
   insufficient,
4. browser validation proves advisor, compliance, client-draft, blocked, degraded, and guardrail
   states where UI support is claimed.

### Slice 12: Live Validation, Canonical Proof, and Operator Evidence

Outcome:

1. extend live validation to request deterministic and AI-assisted narrative where enabled,
2. validate advisor-review and client-draft flows,
3. validate AI-unavailable fallback,
4. emit evidence for generation mode, guardrail status, review state, and latency.

Acceptance gate:

1. live suite validates deterministic narrative without AI dependency,
2. AI-assisted mode is validated where credentials/runtime are available,
3. unavailable AI does not break proposal core flow,
4. guardrail failure path is observable and reproducible,
5. canonical Workbench proof uses the governed front-office runtime when product-surface claims are
   made,
6. evidence is captured under non-git-tracked `output/` and critically reviewed for every material
   field, reason code, evidence ref, lineage ref, review state, latency, and degraded state.

### Slice 13: Commercial, Demo, and Documentation-As-Product Material

Outcome:

1. produce implementation-backed narrative docs, API examples, wiki guidance, demo notes, operator
   material, and sales/pre-sales wording,
2. separate supported deterministic, AI-assisted, client-draft, and client-ready states from target
   roadmap.

Acceptance gate:

1. README/wiki/supported-features material does not exceed implementation,
2. no demo, sales, RFP, regulatory, or AI claim is unsupported,
3. wiki source is updated in the repo and prepared for publication after merge if changed.

### Slice 14: Second-Last Hardening and Review

Outcome:

1. perform a proper code, contract, security, data-mesh, AI-safety, documentation, and operations
   review before closure.

Acceptance gate:

1. API certification pattern compliance is verified,
2. Swagger is complete and contains what/when/how guidance,
3. every request/response attribute has description, type, and example value,
4. error handling, guardrail failures, disclosure failures, model timeout, persistence, replay,
   idempotency, and review transitions are tested,
5. security and sensitive-data controls reject raw prompts, raw model responses, client names,
   portfolio identifiers, holdings, or entitlement details in unsafe logs, metrics, docs, and
   evidence packs,
6. no dead code, duplicate paths, stale docs, or unsupported product claims remain.

### Slice 15: Final Closure

Outcome:

1. update RFC status and index when implemented,
2. update API docs, artifact docs, narrative policy docs, operator runbooks, README, wiki source,
   supported-features, proof summaries, and repo context where behavior changed,
3. update `REPOSITORY-ENGINEERING-CONTEXT.md` if grounded narrative patterns become durable guidance,
4. update platform or agent context if future agents need reusable AI-safety guidance,
5. assess whether skill guidance should change,
6. run stranded-truth reconciliation before final closure,
7. run repo-native local gates, wiki check when docs/wiki changed, GitHub Feature Lane, PR Merge
   Gate, and Main Releasability Gate,
8. publish wiki after merge when wiki source changed,
9. delete local and remote feature branches and leave `local = remote = main`.

Acceptance gate:

1. docs clearly distinguish deterministic evidence from AI-assisted draft text,
2. context/skill changes are either made or explicitly assessed as no-change-needed,
3. RFC index is current,
4. required GitHub checks and Main Releasability Gate are green,
5. branch hygiene leaves `local = remote = main` after merge,
6. no required cross-repo PR, WTBD dependency, unmerged branch, or stranded durable truth remains.

### Slice 16: Post-Completion Communication

Outcome:

1. draft a LinkedIn post only after implementation proof and closure are complete.

Requirements:

1. use the `lotus-linkedin-thought-leadership` workflow,
2. read the content ledger, themes, voice/style guide, and recent drafts before drafting,
3. draft under `lotus-platform/thought-leadership/linkedin/drafts/`,
4. update `content-ledger.md`,
5. keep the post employer-safe, non-confidential, non-promotional, and grounded only in what was
   actually implemented,
6. do not imply any bank or employer uses Lotus,
7. do not make unsupported product, regulatory, investment, or AI claims.

Acceptance gate:

1. post draft exists and ledger is updated, or closure notes record a deliberate no-post decision
   with rationale approved by the user.

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

## Supported-Features Ledger

| Capability | RFC state before implementation | Promotion rule |
| --- | --- | --- |
| Grounding packet builder | Proposed | Promote only after deterministic builder tests prove all material facts come from allowed evidence refs and missing evidence is explicit. |
| Deterministic advisor-review narrative | Proposed | Promote only after template output is stable, source-backed, review-marked, and available without AI dependency. |
| AI-assisted narrative draft | Gated | Promote only after bounded `lotus-ai` or provider adapter execution, prompt/workflow lineage, timeout behavior, unsupported-claim validation, and safe degraded behavior are proven. |
| Client-draft narrative | Proposed | Promote only after disclosure, suitability, risk, approval, and evidence-limitations posture is enforced and review state is visible. |
| Client-ready narrative | Gated | Promote only after explicit human approval, disclosure policy, guardrail pass, report/render/archive readiness, and replay evidence are green. |
| Narrative review workflow | Proposed | Promote only after approve/reject/regenerate transitions are auditable, idempotent where required, and persist exact actor/action/reason/version lineage. |
| Narrative replay | Proposed | Promote only after replay returns the exact persisted narrative evidence without model calls and verifies source-input hashes. |
| Report/render/archive narrative package | Proposed | Promote only after typed package, deterministic rendering, archive record, retention/access-audit refs, and blocked-state behavior are proven. |
| Gateway narrative API | Proposed | Promote only after Gateway consumes canonical Advise endpoints and passes contract/integration tests. |
| Workbench narrative review UX | Proposed | Promote only after browser validation proves backed advisor, compliance, client-draft, blocked, degraded, and guardrail states through Gateway/BFF only. |
| Narrative evidence data product | Proposed | Promote only after producer declaration, trust telemetry, SLO/access/evidence policy, mesh certification, and catalog publication are complete. |
| Sales/demo-safe narrative proof | Proposed | Promote only after synthetic/approved demo data, supported-claim taxonomy, wiki/demo material, and canonical proof are implementation-backed. |

## Existing WTBD Import and No-WTBD Execution Rule

RFC-0023 is the execution source for grounded advisory AI narrative. New WTBD records must not be
created. Existing closed WTBD lessons are imported only as constraints:

| Closed WTBD | Imported RFC-0023 requirement | Slice ownership |
| --- | --- | --- |
| WTBD-001 proposal service decomposition | Narrative implementation must not re-expand `ProposalWorkflowService`; use named grounding, policy, validation, persistence, adapter, and API boundaries. | Slice 2, Slice 5, Slice 10, Slice 14 |
| WTBD-002 stateful context adapter decomposition | Narrative source evidence must preserve source-read, route, cache, taxonomy, translation, and hydration boundaries; richer source fields are source-owned or blocked. | Slice 0, Slice 3, Slice 5, Slice 12 |
| WTBD-003 workspace service decomposition | Workspace narrative integration must not place narrative business logic in API facades or UI helpers; Gateway and Workbench consume canonical Advise contracts. | Slice 2, Slice 8, Slice 11, Slice 14 |
| WTBD-004 Gateway/Workbench capability alignment | Narrative capability and `/platform/capabilities` changes must migrate Gateway and Workbench in the same RFC branch set with source-backed supportability proof. | Slice 4, Slice 11, Slice 12, Slice 14 |

Closure rule:

1. RFC-0023 must have no active WTBD dependency at closure,
2. no cross-repo requirement may be represented only in `WTBD.md`,
3. any existing WTBD lesson relevant to narrative work must appear in slice evidence or closure
   notes,
4. branch cleanup must prove narrative truth is on `main`, not stranded in an unmerged branch or
   side ledger.

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

These must be resolved in Slice 3:

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
9. report/render/archive integration is complete for any client-ready artifact claim,
10. Gateway and Workbench expose only backend-owned narrative through canonical boundaries where UI
    support is claimed,
11. `/platform/capabilities`, supported-features, README, wiki, and demo material claim only
    implementation-backed narrative states,
12. data-product declarations, trust telemetry, mesh certification, SLO/access/evidence policy, and
    supportability posture are complete where a narrative evidence product is promoted,
13. live validation proves ready, blocked, insufficient-evidence, fallback, AI-unavailable, replay,
    review, report/archive, Gateway/Workbench, and guardrail paths where in scope,
14. security and sensitive-data controls prevent raw prompt, raw model output, client-identifying
    data, holdings, restricted telemetry, entitlement details, and unsafe identifiers from leaking
    into logs, metrics, public docs, wiki, or evidence packs,
15. repository-native local gates, wiki check when docs/wiki changed, GitHub Feature Lane, PR Merge
    Gate, and Main Releasability Gate are green,
16. documentation, agent context assessment, skill guidance assessment, wiki publication, branch
    deletion, and local/remote clean-state proof are completed in the final slice,
17. no required follow-up RFC, WTBD dependency, unmerged branch, side ledger, or stranded durable
    truth remains.
