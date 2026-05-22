# RFC-0023 Slice 1: Platform Automation and Scaffolding Review

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0023: Grounded Advisory AI Narrative and Client-Ready Proposal Commentary |
| **Slice** | 1 - platform automation and scaffolding improvement |
| **Status** | IMPLEMENTED - REVIEWED; NO PLATFORM CHANGE REQUIRED |
| **Implemented Date** | 2026-05-22 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0023-slice1-platform-scaffolding` |
| **Capability Posture** | This slice does not implement generated proposal narrative. It proves RFC-0023 can proceed using existing platform and repo-native governance rather than inventing one-off scaffolding. |

## Decision

No `lotus-platform` code or automation change is required before RFC-0023 proceeds to cleanup,
contract, and implementation slices.

The review found that current Lotus automation already covers the reusable scaffolding concerns
needed for the first proposal-narrative implementation wave:

1. API certification and OpenAPI quality,
2. API vocabulary and no-alias governance,
3. domain data product declarations,
4. trust telemetry validation,
5. mesh certification and SLO/access/evidence policy families,
6. repo wiki synchronization and publication,
7. RFC closure governance,
8. heartbeat and delegated-task governance,
9. canonical front-office proof routing when UI evidence becomes part of a later slice.

RFC-0023 must reuse these controls. It must not add local-only narrative proof scripts or local-only
documentation gates unless the pattern is too specific to be useful outside `lotus-advise`.

## Reviewed Automation And Scaffolding

| Review area | Existing control | Slice 1 conclusion |
| --- | --- | --- |
| API certification and Swagger/OpenAPI quality | `make openapi-gate`, `scripts/openapi_quality_gate.py`, OpenAPI contract tests, PR/Main governance jobs | Sufficient for the next API-bearing narrative slice. No platform change required. |
| API vocabulary and no-alias governance | `make api-vocabulary-gate`, `make no-alias-gate`, platform API vocabulary contracts | Sufficient. Any narrative fields added later must pass these gates and avoid alias churn. |
| Bounded observability, health, readiness, and capabilities posture | `GET /platform/capabilities`, `/health/live`, `/health/ready`, supportability metric-label tests, production profile smoke | Sufficient for pre-implementation. Narrative-specific capability rows must be added only when code support exists. |
| Structured logging, correlation, error handling, and problem-details defaults | Existing API tests, route contracts, production guardrail negatives, PR/Main governance jobs | Sufficient for Slice 2 and Slice 3 planning. API-bearing narrative slices must add focused error-path tests rather than a new platform scaffold now. |
| AI workflow-pack safety and evidence scaffolding | Existing `workspace_rationale.pack@v1` integration seam, `lotus-ai` workflow-pack governance, workspace rationale tests | Sufficient as a reference pattern. Proposal narrative must become its own bounded surface and must not reuse workspace-rationale identity. |
| Data-product declarations and trust telemetry | `contracts/domain-data-products/`, `contracts/trust-telemetry/`, `make domain-data-products-gate`, platform mesh contracts | Sufficient. Narrative must not become a declared data product until implemented evidence and trust telemetry exist. |
| SLO, access, evidence policy, and mesh certification | Platform `mesh-slo`, `mesh-access`, `mesh-evidence`, `mesh_certification_gate.py`, mesh runbook | Sufficient. Later slices must add policy files only if a narrative data-product claim is promoted. |
| Live evidence capture | `scripts/run_live_runtime_evidence_bundle.py`, live runtime suite artifacts, PR summary generation | Sufficient for backend advisory proof. Canonical Workbench proof remains routed through `lotus-front-office-runtime` when UI/product-surface proof becomes necessary. |
| Documentation and wiki governance | repo-local `wiki/`, `Sync-RepoWikis.ps1`, documentation layering guidance, docs regression tests | Sufficient. This RFC will keep wiki source concise and publish after merge when wiki truth changes. |
| Heartbeat and long-running monitoring | Platform heartbeat contracts and automation, PR watch through GitHub checks | Sufficient. Use heartbeat patterns for long-running cross-repo or async monitoring only when they add visibility; do not add heartbeat artifacts for small local doc/code slices. |

## Rejected One-Off Local Scaffolding

This slice deliberately rejects these local additions:

1. a `lotus-advise`-only RFC-slice validator,
2. a local proposal-narrative proof format before the narrative contract exists,
3. a local AI guardrail scaffold before the proposal narrative workflow-pack boundary is chosen,
4. a local mesh certification substitute,
5. local wiki publication logic outside the platform `Sync-RepoWikis.ps1` flow.

Those would add maintenance cost without improving RFC-0023 execution. When a later slice discovers
a repeatable gap, the change must go to `lotus-platform` with platform-native tests.

## Required Controls For Later RFC-0023 Slices

| Later slice need | Required control |
| --- | --- |
| New narrative request/response contract | `make openapi-gate`, OpenAPI contract tests, API vocabulary gate, no-alias gate |
| New narrative capability row | `/platform/capabilities` tests plus conservative wiki-supported-features wording |
| AI workflow-pack integration | lotus-ai workflow-pack contract, run lineage, supportability posture, degraded-state tests |
| Persisted narrative versions | migration smoke, replay tests, idempotency/correlation tests, audit/lineage tests |
| Narrative data-product claim | repo-native producer declaration, trust telemetry snapshot, SLO/access/evidence policy, mesh certification |
| Gateway/Workbench consumption | Gateway contract tests, Workbench BFF-only tests, canonical front-office runtime proof where product UI support is claimed |
| Documentation and demo truth | README/wiki/docs updates with implementation-backed claims only, wiki check before merge, wiki publish after merge |

## No Platform Change Rationale

The current gap is not missing platform automation. The current risk is scope discipline:

1. not reusing workspace rationale as if it were proposal narrative,
2. not promoting client-ready commentary before policy/disclosure/review/report/archive proof,
3. not declaring a narrative data product before implementation-backed telemetry exists,
4. not letting UI, report, or demo prose infer text locally.

Those risks are better handled by RFC-0023 source maps, contract tests, API gates, and supported
feature truth than by adding a new platform automation surface now.

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Stranded-truth reconciliation | `git fetch origin --prune` and `git branch -r --no-merged origin/main` returned no unmerged remote branches before Slice 1 implementation. |
| Platform automation review | Reviewed `lotus-platform` RFC closure governance, repo wiki sync tests, mesh contracts, trust telemetry contracts, heartbeat contracts, and repository-governance automation. |
| Repo-native gate review | Reviewed `lotus-advise` `Makefile`, Feature Lane, PR Merge Gate, Main Releasability Gate, live runtime evidence bundle helpers, capabilities tests, and docs contract tests. |
| No one-off scaffold decision | Recorded explicit rejection of local-only RFC-slice, mesh, wiki, and narrative-proof scaffolding. |
| Next-slice readiness | RFC-0023 may proceed to Slice 2 cleanup and structure using existing platform and repo-native gates. |

## Wiki And README Decision

Wiki source is updated because RFC implementation status and product-roadmap truth changed. README
does not change in this slice because command surfaces, runtime behavior, and supported feature
entrypoints did not change.
