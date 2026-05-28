# Operations Runbook

## Health Endpoints

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

## Readiness Meaning

Readiness is not a cosmetic check. Startup and readiness validate:

1. advisory runtime persistence posture
2. proposal repository boot readiness
3. proposal async runtime recovery posture

If the service cannot satisfy the advisory persistence contract, readiness should fail closed.

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

## Advisor Cockpit Operations

RFC-0026 cockpit supportability is exposed through `GET /advisory/cockpit/supportability` and
`GET /platform/capabilities`. The supported first-wave posture is source-owned advisor workflow
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
2. runtime posture must not contain credentials, query strings, fragments, secrets, tokens,
   prompts, raw payloads, trace IDs, or correlation IDs
3. endpoint posture should use bounded integer `latency_ms` values, not raw traces or request
   payloads
4. local `output/` artifacts are evidence, not authored documentation source; README and wiki truth
   must be updated separately when implementation posture changes
5. client-ready publication, external client communication, bank-specific attestations,
   legal/regulatory advice, completed policy sign-off/approval, and OMS/order/fill/settlement stay
   blocked unless separately implemented and proven

Use `docs/commercial/RFC-0028-bank-demo-client-proof-materials.md` for sales, pre-sales, RFP, and
demo-lead wording. It is the business-facing guide, but it remains constrained by the supported
claim register and proof-pack evidence.

## Canonical Local Identity

Use:

- `http://advise.dev.lotus`

That is the canonical local service identity for cross-app and demo-oriented flows.

## Postgres Rollout Notes

The active runtime direction is PostgreSQL-backed proposal lifecycle persistence.

Operationally important commands from the rollout runbook:

```bash
python scripts/postgres_migrate.py --target all
python scripts/production_cutover_check.py --check-migrations
```

Use the full runbook in `docs/documentation/postgres-migration-rollout-runbook.md` for rollout,
smoke, and fix-forward guidance.
