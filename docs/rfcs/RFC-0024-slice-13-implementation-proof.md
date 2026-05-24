# RFC-0024 Slice 13: Implementation Proof

## Status

Implemented for `lotus-advise` live-suite memo proof coverage and machine-readable evidence
artifacts.

This slice does not promote active `AdvisoryProposalMemoEvidencePack:v1` data-product support,
full RFC-0028 bank-demo/RFP package claims, client-ready memo publication, send-to-client controls,
or external client communication.

## Purpose

Slice 13 closes the memo implementation-proof gap by making the existing live runtime suite prove
the advisor-use memo journey instead of relying only on unit, contract, API, Gateway, Workbench,
report, render, archive, AI, or commercial-material evidence in isolation.

The proof path stays in the governed live evidence bundle:

1. output is written under non-git-tracked `output/`,
2. JSON and Markdown summaries are generated from one typed result object,
3. PR summaries are rendered from captured bundle artifacts,
4. client-ready attempts are explicitly checked as blocked states, not inferred from docs.

## Implemented Behavior

`scripts/validate_cross_service_parity_live.py` now adds a `proposal_memo` proof snapshot to the
sequential live parity result. The snapshot covers the Advise memo
create/read/projection/review/report-package/AI-commentary/lineage/replay route family.

The memo proof creates a stateful proposal from canonical upstream source context, proving the
stateful source dependency path before memo creation, then validates:

1. memo create and immutable read with exact `memo_hash` continuity,
2. advisor audience projection with `client_ready_publication=BLOCKED`,
3. stale memo-hash review rejection,
4. client-ready memo-review rejection,
5. `APPROVE_FOR_ADVISOR_USE` review posture against the persisted memo hash,
6. client-ready report-document rejection,
7. advisor-use report/render/archive package request, recording success refs when downstream
   materialization is available and a deterministic degraded reason when `lotus-report` is not,
8. review-gated memo AI commentary through the existing `proposal_memo_commentary.pack@v1` path,
   including `authoritative_for_memo_status=false` and `review_required=true`,
9. memo lineage completeness and memo count,
10. memo replay evidence with exact memo hash, source-input hash, and blocked client-ready
    publication posture.

`scripts/live_runtime_proposal_memo.py` owns the typed extraction model so the live-suite artifact
writer does not contain memo business rules.

`scripts/live_runtime_suite_artifacts.py` now renders memo proof into:

1. `result.json`,
2. `summary.md`,
3. `pr-summary.md`.

## Proof Coverage Map

| RFC-0024 Slice 13 acceptance item | Implemented proof |
| --- | --- |
| Advise APIs | Live suite exercises create/read/projection/review/report-package/AI-commentary/lineage/replay memo endpoints. |
| Source dependencies | The memo proposal is created through the stateful canonical source path already used by live parity proof. |
| Gateway and Workbench | Slice 11 remains the canonical cross-repo product realization proof; this slice records memo proof in the backend evidence bundle consumed by PR evidence. |
| Report/render/archive | Advisor-use memo report package request records downstream refs when available; unavailable downstream materialization is retained as a deterministic degraded reason. |
| AI when enabled | The memo AI endpoint is exercised through the review-gated commentary path and records deterministic unavailable posture when AI is not configured. |
| `/platform/capabilities` | Existing live suite keeps capability checks for reporting and reviewed-narrative posture; memo data-product capability remains intentionally unpromoted. |
| Health/readiness | The live suite still runs only against the configured live service stack and fails fast on unavailable required services. |
| Degraded scenarios | Memo report materialization records a deterministic degraded reason; existing degraded runtime drills remain part of the suite. |
| Critical review of figures, reason codes, refs, lineage, statuses, hashes, redactions, degraded states | The memo snapshot records hashes, source hashes, review action, report/render/archive refs, AI authority posture, replay posture, and blocked client-ready reason codes. |

## Local Validation

Targeted validation for this slice:

1. `python -m pytest tests/unit/advisory/api/test_live_runtime_suite.py -q`
2. `python -m ruff check scripts/validate_cross_service_parity_live.py scripts/live_runtime_proposal_memo.py scripts/live_runtime_suite_artifacts.py tests/unit/advisory/api/test_live_runtime_suite.py`

Full closure still requires:

1. `make check` in `lotus-advise`,
2. repo wiki drift check before merge,
3. PR Feature Lane and PR Merge Gate green,
4. main releasability green after merge,
5. wiki publication and `DiffCount 0` after merge.

Optional live proof command when the governed stack is available:

```powershell
python scripts/validate_live_runtime_suite.py --output-dir output/rfc0024-slice13
python scripts/render_live_runtime_pr_summary.py --bundle-dir output/rfc0024-slice13
```

## Remaining Gates

Slice 13 does not promote:

1. active supported data-product posture for `AdvisoryProposalMemoEvidencePack:v1`,
2. mesh-certified memo evidence-product access, SLO, lifecycle, and evidence-policy posture,
3. full RFC-0028 bank-demo/RFP proof-pack claims,
4. client-ready memo publication,
5. client-ready report package release,
6. send-to-client or external client communication behavior.
