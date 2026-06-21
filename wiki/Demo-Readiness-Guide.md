# Demo Readiness Guide

This page is the fast preparation guide for a `lotus-advise` demo. It is written for business
reviewers, sales and pre-sales, operations, and engineers who need a shared, implementation-backed
view of what can be shown.

Use this guide together with [Demo and Commercial Proof](Demo-and-Commercial-Proof), [Supported
Features](Supported-Features), and `docs/commercial/RFC-0028-bank-demo-client-proof-materials.md`.

## What The Demo Can Safely Show

| Demo area | Safe current message | Evidence to check |
| --- | --- | --- |
| Advisory journey | Lotus Advise can show a governed private-banking advisory proof journey for the canonical scenario. | Scenario `RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL`, portfolio `PB_SG_GLOBAL_BAL_001`, proof marker `BANK_DEMO_PROOF_PACK_CREATED`. |
| Proposal lifecycle | Advisory proposal state, immutable versions, approvals, consent posture, and execution-readiness posture are source-owned by Advise. | Proposal lifecycle APIs, workflow events, and proposal version evidence. |
| Narrative, memo, and policy evidence | Advisor-review and advisor-use evidence can be shown with lineage, review posture, and blocked client-ready boundaries. | Narrative, memo, policy, report/render/archive lineage, and supported-feature posture. |
| AI-assisted evidence | AI support is review-assistive, bounded, and non-authoritative. | Lotus AI lineage, guardrail posture, and unavailable fallback behavior. |
| Bank-demo proof pack | Demo and RFP language is tied to a supported-claim register and sanitized proof pack. | `supported-claim-register.json`, `proof-pack.json`, `material-field-review.json`, and `commercial-material-pack.json`. |
| Workbench proof surface | Workbench can render Gateway-backed proof for the governed panel after canonical validation passes. | Canonical front-office validation for `PB_SG_GLOBAL_BAL_001`. |

## Stop Conditions

Stop and fix the evidence before using demo material when any of these is true:

1. the latest implementation is not merged to `main`,
2. required PR or Main Releasability checks are red,
3. `GET /health/ready` is not healthy for the runtime under test,
4. `GET /platform/capabilities` does not expose the expected advisory proof posture,
5. canonical validation for `PB_SG_GLOBAL_BAL_001` has not passed,
6. `material-field-review.json` reports a blocked material field,
7. proof artifacts contain secrets, credentials, access tokens, unredacted AI inputs, unredacted
   source evidence, trace IDs, correlation IDs, or local-only runtime paths,
8. a demo answer would require claiming client-ready publication, external client communication,
   legal/regulatory advice, bank-specific certification, completed approval/sign-off authority, or
   OMS/order/fill/settlement.

## Preparation Checklist

| Step | Owner | Command or artifact |
| --- | --- | --- |
| Confirm repo state | Engineering | Latest PR merged to `main`; Main Releasability green. |
| Validate backend quality | Engineering | `make check` and relevant PR Merge Gate evidence. |
| Validate live app proof | Engineering or operations | `make demo-certification-live` against the intended runtime. |
| Validate front-office proof | Demo lead or operations | Governed Workbench canonical validation for `PB_SG_GLOBAL_BAL_001`. |
| Review proof pack | Demo lead | `scenario-contract.json`, `supported-claim-register.json`, `proof-pack.json`, `runtime-posture.json`, `material-field-review.json`, `document-proof-summary.json`, `journey-integration-proof-summary.json`, `commercial-material-pack.json`. |
| Prepare talk track | Sales or pre-sales | `docs/commercial/RFC-0028-bank-demo-client-proof-materials.md`. |
| Prepare operator notes | Operations | [Operations Runbook](Operations-Runbook) and [Troubleshooting](Troubleshooting). |

## Audience Notes

### Business Reviewers

Focus on the advisory operating model:

1. source evidence is preserved,
2. review posture is visible,
3. unsupported claims are blocked rather than hidden,
4. proof artifacts explain what is implemented and what remains outside current support.

### Sales And Pre-Sales

Use the claim-controlled commercial guide. Do not create independent claims from screenshots or
draft slides. Safe language should describe implemented advisor proof, review posture, evidence
lineage, and blocked boundaries.

### Operations

Treat the demo like a controlled runtime event. Confirm health, readiness, capability posture,
canonical validation, and proof-pack review before screenshots or playback.

### Engineers

Trace behavior through:

1. [API Surface](API-Surface),
2. [Integrations](Integrations),
3. [Validation and CI](Validation-and-CI),
4. `docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md`.

## Safe Talk Track

"This demo shows how Lotus Advise makes a private-banking advisory journey explainable,
reviewable, and evidence-backed. It shows advisor-review and advisor-use posture, source lineage,
AI/model-risk boundaries, policy and cockpit evidence, and claim-controlled proof material. It also
shows where the platform deliberately blocks unsupported claims."

## Claims That Must Stay Blocked

Do not claim:

1. client-ready publication or send-to-client approval,
2. external client communication,
3. legal or regulatory advice,
4. completed policy approval, waiver, or sign-off authority,
5. AI approval or autonomous recommendation authority,
6. OMS order, fill, settlement, or execution system-of-record behavior,
7. bank-specific security, compliance, regulatory, or production certification.

## Quick Links

- [Demo and Commercial Proof](Demo-and-Commercial-Proof)
- [Supported Features](Supported-Features)
- [API Surface](API-Surface)
- [Operations Runbook](Operations-Runbook)
- [Validation and CI](Validation-and-CI)
- `docs/demo/README.md`
- `docs/commercial/RFC-0028-bank-demo-client-proof-materials.md`
