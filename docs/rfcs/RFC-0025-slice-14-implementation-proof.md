# RFC-0025 Slice 14: Implementation Proof

## Status

Implemented for `lotus-advise` live-suite policy evaluation proof coverage and machine-readable
evidence artifacts.

This slice does not promote active `AdvisoryPolicyEvaluationRecord:v1` data-product support,
completed approval or waiver authority, completed policy sign-off authority, client-ready policy
document publication, external client communication, or full RFC-0028 bank-demo/RFP package claims.

## Purpose

Slice 14 closes the policy-pack implementation-proof gap by making the governed Advise live runtime
suite exercise the policy evaluation journey as one replayable proof path. Earlier slices proved
the catalog, evaluation engine, persistence, certified APIs, workflow, report-package, AI boundary,
Gateway/Workbench product realization, and commercial wording separately. This slice ties the
business journey together in the evidence bundle instead of relying on isolated unit, API, or UI
proof.

The proof path stays in the governed live evidence bundle:

1. output is written under non-git-tracked `output/`,
2. JSON and Markdown summaries are generated from one typed result object,
3. PR summaries are rendered from captured bundle artifacts,
4. fail-closed paths are checked as explicit blocked states, not inferred from docs.

## Implemented Behavior

`scripts/validate_cross_service_parity_live.py` now adds a `proposal_policy` proof snapshot to the
sequential live parity result. The snapshot covers the Advise policy evaluation
create/read/review-queue/workflow/sign-off-package/sign-off-decision/report-package/AI-evidence/
lineage/replay route family.

The policy proof creates a policy evaluation for `SG_PRIVATE_BANKING_REFERENCE` `2026.05`, ensuring
the reference pack is active first, then validates:

1. policy evaluation create and immutable read with exact `evaluation_hash`,
   `source_evidence_hash`, and `policy_content_hash` continuity,
2. material rule results, source refs, source gaps, approval dependencies, disclosure
   requirements, consent requirements, and pending-review posture,
3. review queue posture for the finalized policy record,
4. workflow posture, SLA open-requirement count, client-ready publication block, and sign-off
   readiness,
5. sign-off source package behavior before decision recording,
6. stale source-evaluation-hash sign-off rejection,
7. sign-off decision recording after approval, disclosure, and consent requirements are resolved,
8. client-ready policy document request rejection,
9. advisor/compliance-use report-package request after sign-off, recording report/render/archive
   refs when downstream materialization is available and a deterministic degraded reason when it
   is not,
10. forbidden AI policy action rejection through `POLICY_AI_EVIDENCE_FORBIDDEN_ACTION`,
11. bounded AI evidence through `policy_evidence_summary.pack@v1`, including
    `authoritative_for_policy_status=false`, `human_review_required=true`, and
    `raw_source_evidence_included=false`,
12. lineage completeness and audit-event count,
13. replay evidence with exact evaluation hash and source-evidence hash comparison.

`scripts/live_runtime_policy_evaluation.py` owns the typed extraction model so the live-suite
artifact writer does not contain policy business rules.

`scripts/live_runtime_suite_artifacts.py` now renders policy proof into:

1. `result.json`,
2. `summary.md`,
3. `pr-summary.md`.

## Proof Coverage Map

| RFC-0025 Slice 14 acceptance item | Implemented proof |
| --- | --- |
| Advise APIs | Live suite exercises policy evaluation create/read/review-queue/workflow/sign-off-package/sign-off-decision/report-package/AI-evidence/lineage/replay endpoints. |
| Source dependencies | The policy proof uses source refs, source gaps, approval dependencies, disclosures, and consents carried by the policy evaluation record instead of inventing source facts. |
| Gateway and Workbench | Slice 12 remains the canonical cross-repo product realization proof; this slice records backend policy proof in the live evidence bundle consumed by PR evidence. |
| Report/render/archive | Signed-off advisor/compliance-use policy report package request records downstream refs when available; unavailable downstream materialization is retained as a deterministic degraded reason. |
| AI when enabled | The policy AI endpoint is exercised through the bounded evidence path and records deterministic unavailable posture when AI is not configured. |
| `/platform/capabilities` | Policy data-product capability remains intentionally unpromoted until active data-product promotion; the proof keeps capability claims out of the Advise capability source. |
| Mesh certification | The data-product declaration and trust telemetry remain blocked but now reference Slice 14 implementation proof as evidence. |
| Health/readiness | The live suite still runs only against the configured live service stack and fails fast on unavailable required services. |
| Degraded scenarios | Policy report materialization records a deterministic degraded reason; existing degraded runtime drills remain part of the suite. |
| Critical review of figures, reason codes, refs, lineage, statuses, hashes, redactions, approval dependencies, disclosures, consents, SLA, degraded states | The policy snapshot records hashes, material rule counts, source gap counts, requirement counts, workflow state, sign-off state, report/render/archive refs, AI authority and redaction posture, lineage, replay posture, blocked client-ready reason codes, and latency. |

## Local Validation

Targeted validation for this slice:

1. `python -m ruff check scripts/validate_cross_service_parity_live.py scripts/live_runtime_policy_evaluation.py scripts/live_runtime_suite_artifacts.py tests/unit/advisory/api/test_live_runtime_suite.py`
2. `python -m pytest tests/unit/advisory/api/test_live_runtime_suite.py tests/unit/advisory/api/test_api_advisory_policy_evaluations.py -q`

Full closure still requires:

1. `make check` in `lotus-advise`,
2. governed live-suite evidence under `output/rfc0025-slice14`,
3. canonical front-office runtime validation when the governed Workbench stack is available,
4. repo wiki drift check before merge,
5. PR Feature Lane and PR Merge Gate green,
6. main releasability green after merge,
7. wiki publication and `DiffCount 0` after merge.

Live proof command when the governed stack is available:

```powershell
python scripts/validate_live_runtime_suite.py --output-dir output/rfc0025-slice14
python scripts/render_live_runtime_pr_summary.py --bundle-dir output/rfc0025-slice14
```

## Remaining Gates

Slice 14 does not promote:

1. active supported data-product posture for `AdvisoryPolicyEvaluationRecord:v1`,
2. mesh-certified active policy evidence-product access, SLO, lifecycle, and evidence-policy
   posture,
3. completed approval or waiver authority,
4. completed policy sign-off authority,
5. client-ready policy document generation or publication,
6. external client communication,
7. full RFC-0028 bank-demo/RFP proof-pack claims.
