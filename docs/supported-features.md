# Lotus Advise Supported Features

This document records current supported-feature posture without overclaiming production or bank
certification readiness.

For the fuller operator-facing matrix, use `wiki/Supported-Features.md`. For demo preparation, use
`wiki/Demo-Readiness-Guide.md` and
`docs/commercial/RFC-0028-bank-demo-client-proof-materials.md`.

## Supported In Current Repo Gates

| Capability family | Current support | Primary evidence |
| --- | --- | --- |
| Advisory proposal simulation and artifact | Supported for governed advisory scenarios and deterministic proposal artifact generation. | Unit, integration, OpenAPI, and demo payload tests. |
| Proposal lifecycle | Supported for persisted proposal creation, immutable versions, transitions, approvals, consent posture, delivery posture, and execution-readiness posture. | Proposal lifecycle tests, Postgres migration smoke, and workflow contract docs. |
| Advisory workspace | Supported for draft, save, resume, compare, rationale, and lifecycle handoff flows with Postgres-backed workspace session and saved-version state in production runtime. | Workspace API, engine, repository, migration, and runtime persistence tests. |
| Proposal narrative evidence | Supported for advisor-review posture, review/replay, report-package propagation, report/render/archive lineage, Gateway/Workbench exposure, and data-product/trust posture. | RFC-0023 contract tests and supported-feature wiki truth. |
| Proposal memo evidence | Supported for advisor-use memo posture, review-gated AI commentary, report/render/archive lineage, Gateway/Workbench exposure, and evidence-pack data-product posture. | RFC-0024 contract tests, commercial guide, and supported-feature wiki truth. |
| Policy-pack evidence | Supported for policy-pack catalog, evaluation records, workflow/sign-off posture, report-package lineage, bounded AI evidence, Gateway/Workbench exposure, and active data-product posture. | RFC-0025 contract tests, commercial guide, and trust telemetry validation. |
| Advisor cockpit | Supported for source-owned action items, operating snapshots, supportability, acknowledgements, Gateway/Workbench consumption, and canonical proof posture. | RFC-0026 tests and wiki supported-feature matrix. |
| Advisory copilot | Supported for governed evidence packets, approved `lotus-ai` provider/model inventory enforcement, claim-level source grounding, guardrails, workflow-pack integration, trusted-principal run review, maker-checker audit, retention, certified APIs, and product-realization proof. Unknown, retired, mismatched, or environment-incompatible model identity returns unavailable; unsupported or unverifiable AI claims remain not review-ready, and request-body actor fields cannot authorize review actions. | RFC-0027 tests, model-governance tests, and API contract evidence. |
| Bank-demo proof | Supported for scenario contract, supported-claim register, sanitized proof-pack capture, commercial material pack, Gateway/Workbench proof surface, and blocked-claim governance. | RFC-0028 tests, `wiki/Demo-Readiness-Guide.md`, and `docs/commercial/RFC-0028-bank-demo-client-proof-materials.md`. |
| API governance | Enforced for OpenAPI quality, no-alias behavior, API vocabulary, domain data products, trust telemetry freshness, architecture boundaries, complexity regression, high-severity security findings, dependency-lock evidence, and license/IP release evidence. | `make check`, `make trust-telemetry-freshness-gate`, `make dependency-lock-gate`, `make license-ip-gate`, Feature Lane, PR Merge Gate, Main Releasability. |

## Explicit Boundaries

- No claim of final client-ready publication approval.
- No claim of legal, regulatory, compliance, or bank certification signoff.
- No claim of OMS/order/fill/settlement support unless separately implemented and proven.
- No claim that Workbench reconstructs advisory, suitability, memo, policy, narrative, or AI
  semantics locally; it consumes governed Gateway/Advise contracts.
- No claim that AI approves recommendations, policy posture, sign-off, or client communication.
- Quality baseline reports are evidence for progressive hardening, not final production readiness.

## How To Use This Page

- Business and demo reviewers should start with the supported and blocked capability families.
- Sales and pre-sales should use the commercial guide for exact wording.
- Operations should use the wiki runbook and proof-pack stop conditions before playback.
- Engineers should use the linked RFCs, route docs, and repo-native gates before changing support
  posture.
