# Operations Runbook

## Health Endpoints

- `GET /health`
- `GET /health/live`
- `GET /health/ready`
- `GET /version`

## Readiness Meaning

Readiness is not a cosmetic check. Startup and readiness validate:

1. advisory runtime persistence posture
2. proposal repository boot readiness
3. proposal async runtime recovery posture

If the service cannot satisfy the advisory persistence contract, readiness should fail closed.

`GET /version` is not a readiness check. It exposes support-safe build and image metadata so
operators can compare a running container with Main Releasability release evidence.

## Release Image Operations

Release images are pushed only by the Main Releasability Gate. The release image must be tagged with
the Git SHA and accompanied by retained evidence:

1. digest-bearing `release-evidence.json`,
2. SBOM,
3. vulnerability scan report,
4. image signature,
5. provenance attestation.

Deployment should use the immutable image digest from the release manifest and promote that same
image across environments. Do not rebuild per environment, and do not inject secrets through Docker
build args, OCI labels, release manifests, or `/version` metadata.

## Advisory Supportability Metrics

`GET /platform/capabilities` publishes the implemented feature key
`advise.observability.advisory_supportability` and a source-backed `supportability` summary. The
summary reports only bounded operational posture:

1. `state`
2. `reason`
3. `freshness_bucket`
4. dependency and feature readiness counts

`/metrics` emits `lotus_advise_advisory_supportability_total` with `state`, `reason`, and
`freshness_bucket` labels only. The `supportability.metric_labels` response field must match this
metric exactly. Do not add portfolio, account, client, advisor, proposal, workspace, request,
response, correlation, trace, transaction, security, or payload identifiers to this metric.

## Risk Authority Degradation

Proposal authority evidence must stay internally consistent when `lotus-risk` is unavailable. If
`authority_resolution.risk_authority` is `unavailable`, `authority_resolution.degraded` is `true`
and `degraded_reasons` contains a stable reason. Dependency configuration/readiness failures use
`LOTUS_RISK_DEPENDENCY_UNAVAILABLE`; configured enrichment failures use
`LOTUS_RISK_ENRICHMENT_UNAVAILABLE`. Do not infer local risk metrics when either reason is present.

## Policy Evaluation Diagnostics

Use `GET /advisory/policy-evaluations/{evaluation_id}/diagnostics` when support needs one
bounded view of policy-evaluation posture. The projection is derived from the finalized policy
evaluation record and append-only audit events. It reports sign-off status, latest review,
sign-off, report-package and AI evidence event summaries, report-package handoff posture, AI
fallback posture, replay hashes, safe next action, and this runbook reference.

Diagnostics must stay support-safe. Do not add raw source evidence, raw downstream report or AI
payloads, prompt text, unrestricted exception details, credentials, trace identifiers, correlation
identifiers, client secrets, or portfolio/account payloads to this endpoint.

## Report Package Status Recovery

Advisor memo and policy sign-off report packages preserve `lotus-report` as the report/render/
archive owner. Advise submits the report job, performs bounded status retrieval, and keeps the
report job id in the response even when the downstream status is not terminal.

Operational interpretation:

1. `ARCHIVED` means `lotus-report` returned terminal archive evidence.
2. `ACCEPTED`, `RUNNING`, and `PENDING_ARCHIVE` are not archive-ready states.
3. `REPORT_STATUS_UNAVAILABLE` means the status URL was missing/unsafe, the status lookup failed,
   or the status payload was malformed. Operators should use the preserved report job id and
   idempotency key to inspect `lotus-report`.
4. `FAILED` means the downstream report/render/archive workflow reached a terminal failure and
   should be escalated to the report/render/archive owner.

## Advisor Cockpit Operations

RFC-0026 cockpit supportability is exposed through `GET /advisory/cockpit/supportability` and
`GET /platform/capabilities`. The supported posture is source-owned advisor workflow
evidence: action items, snapshot posture, acknowledgement replay, active data products, Gateway
publication, Workbench rendering, and canonical `PB_SG_GLOBAL_BAL_001` proof.

Operationally, cockpit acknowledgements are not remediation authority. Treat them as append-only
advisor workflow evidence. They must not be used as proof of completed policy approval, client
communication, CRM system-of-record task creation, or OMS order/fill/settlement activity.

## RFC-0028 Bank Demo Proof Operations

RFC-0028 proof capture is repeatable and evidence-backed for the governed canonical portfolio
`PB_SG_GLOBAL_BAL_001`. The expected proof marker is `BANK_DEMO_PROOF_PACK_CREATED`; material drift
is represented by `RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED` or an HTTP 409 response from the
proof-pack API.

Use one of these capture modes:

```bash
python scripts/capture_rfc0028_backend_proof.py --live-suite-json <path> --output-dir output/rfc0028/backend-proof
python scripts/capture_rfc0028_backend_proof.py --run-live-suite --output-dir output/rfc0028/backend-proof
```

When `--output-dir` is absolute or outside the governed default path, set `--artifact-ref-prefix`
to a relative proof-artifact reference such as `output/rfc0028/backend-proof`. The filesystem
location may vary by operator, but proof-pack asset references must stay portable, local-relative,
and free of URL/query/fragment/traversal or sensitive credential or AI-input material.

Review these artifacts before reusing demo, RFP, security, or proof-guide material:

1. `proof-pack.json`
2. `scenario-contract.json`
3. `supported-claim-register.json`
4. `runtime-posture.json`
5. `sanitized-runtime-summary.json`
6. `material-field-review.json`
7. `document-proof-summary.json`
8. `journey-integration-proof-summary.json`
9. `commercial-material-pack.json`
10. `capture-summary.md`

Operational interpretation:

1. a material-review block or HTTP 409 is a defect to triage at the source layer; do not work
   around it in Workbench, Gateway, or documentation
2. runtime posture must not contain credentials, query strings, fragments, unredacted AI inputs,
   unrestricted runtime payloads, trace identifiers, or correlation identifiers
3. ready `/platform/capabilities` runtime evidence must include feature
   `advisory.bank_demo_proof` and workflow `advisory_bank_demo_proof`; missing keys indicate stale
   capability discovery and block proof-pack reuse
4. live-suite result refs, live-suite bundle refs, and output ref prefixes must be local relative
   artifact references; URL/query/fragment/traversal and sensitive credential or AI-input material
   is rejected
5. HTTP 422 request-validation responses should name the invalid field and rule without echoing the
   rejected sensitive value
6. endpoint posture should use bounded integer `latency_ms` values, not unrestricted traces or
   request payloads
7. local `output/` artifacts are evidence, not authored documentation source; README and wiki truth
   must be updated separately when implementation posture changes
8. client-ready publication, external client communication, bank-specific attestations,
   legal/regulatory advice, completed policy sign-off/approval, and OMS/order/fill/settlement stay
   blocked unless separately implemented and proven

For `lotus-advise` app-level demo certification, run:

```bash
make demo-certification-live
```

The command validates the live service readiness, OpenAPI route-safety posture, deterministic
synthetic advisory scenarios, required `/platform/capabilities` feature/workflow truth, and domain
assertions, then writes evidence under `output/demo-certification/`. The scheduled/manual Postgres
runtime workflow uploads the same evidence artifact. Treat any non-zero exit or unsafe route probe
as a release-blocking defect for the demo scope.

Use `docs/commercial/RFC-0028-bank-demo-client-proof-materials.md` for sales, pre-sales, RFP, and
demo-lead wording. It is the business-facing guide, but it remains constrained by the supported
claim register and proof-pack evidence.

## Canonical Local Identity

Use:

- [canonical local service identity](http://advise.dev.lotus)

That is the canonical local service identity for cross-app and demo-oriented flows.

## Postgres Rollout Notes

The active runtime direction is PostgreSQL-backed proposal lifecycle and policy evidence
persistence. Proposal state uses the `proposals` migration namespace. Policy-pack catalog,
policy-evaluation records, audit events, and idempotency maps use the `policy_packs` migration
namespace and are composed through runtime repository ports.

Operationally important commands from the rollout runbook:

```bash
python scripts/postgres_migrate.py --target all
python scripts/production_cutover_check.py --check-migrations
```

Use the full runbook in `docs/documentation/postgres-migration-rollout-runbook.md` for rollout,
smoke, and fix-forward guidance.

Proposal workflow events and approval history are indexed for the supported hot reads:

- `proposal_workflow_events (proposal_id, occurred_at, event_id)`,
- `proposal_approvals (proposal_id, occurred_at, approval_id)`.

These support single-proposal history/replay and batched Advisor Cockpit/source-loader reads.
Validate query shape and retention evidence before adding broader lifecycle-history indexes.
