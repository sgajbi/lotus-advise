# Lotus Advise Operations Runbook

## Local Validation

- `make check`: local Feature Lane parity for lint, typecheck, OpenAPI, vocabulary, data-product,
  and unit-test gates.
- `make ci-local`: local PR Merge Gate subset without Docker, including quality-baseline
  freshness.
- `make quality-baseline`: regenerate report-only quality artifacts in `quality/`.
- `make engineering-health`: regenerate the structural engineering-health baseline.
- `make demo-certification-live`: run live app-level demo certification against
  `LOTUS_ADVISE_DEMO_BASE_URL` or `http://127.0.0.1:8000`, writing machine-readable evidence to
  `LOTUS_ADVISE_DEMO_EVIDENCE` or
  `output/demo-certification/latest/lotus-advise-demo-certification.json`.

## Runtime Validation

- `make migration-smoke`: migration and runtime persistence smoke tests.
- `make postgres-runtime-contracts-local`: local Postgres runtime contract checks.
- `make production-profile-guardrail-negatives-local`: production-profile negative guardrail
  checks.
- `make docker-build`: Docker image build validation.
- `make release-image-provenance-gate`: static Dockerfile, OCI label, release metadata, and
  support-safe build metadata contract validation.
- `make bandit-severity-regression-gate`: Bandit security gate that blocks all high findings and
  fails on new, stale, expired, or worsened medium/low findings relative to the governed baseline.

## Required Runtime Identity

Production-like report and AI integrations require `LOTUS_ADVISE_TENANT_ID` to contain the trusted
tenant identifier propagated to downstream boundaries. Report requests also require a bounded
`requested_by` actor in the advisory request payload. Missing, blank, over-length, or
control-character-containing values fail closed before `lotus-report` or `lotus-ai` HTTP
submission.

Report requests additionally require source-derived as-of date, reporting currency, and proposal
jurisdiction metadata. The service does not manufacture current-date, USD, or SG fallbacks for
production-like downstream report submissions.

## Release Image Evidence

Runtime build identity is exposed at `GET /version`. Operators should compare it with the retained
Main Releasability image release evidence before promoting or diagnosing a container:

1. image tag must be the Git SHA,
2. OCI labels must carry commit, branch/ref, repository URL, service version, build timestamp, CI
   run ID, and image-digest posture,
3. `release-evidence.json` must carry the pushed image digest plus SBOM, vulnerability scan,
   signature, and provenance-attestation references,
4. production deployment must use the immutable digest reference and promote the same image across
   environments instead of rebuilding,
5. Docker build args, environment variables, OCI labels, release manifests, and runtime `/version`
   metadata must remain support-safe and must not carry secrets or DSNs.
6. release evidence must link Bandit, dependency audit, SBOM, and container vulnerability-scan
   artifacts so security posture is reviewable with the immutable image identity.

## Operational Posture

- Treat GitHub Actions as CI truth.
- Treat `quality/` reports as baseline evidence, not production-readiness signoff.
- Publish wiki only when repo-local `wiki/` source changes.

## Proposal History Reads

Proposal workflow events and approvals are indexed for bounded history reads by proposal and
occurrence time:

- `proposal_workflow_events`: `(proposal_id, occurred_at, event_id)`,
- `proposal_approvals`: `(proposal_id, occurred_at, approval_id)`.

These indexes support single-proposal detail/replay reads and batched Advisor Cockpit/source-loader
history reads. Before adding broader history indexes, validate the concrete query path and retention
profile so proposal lifecycle storage does not accumulate unowned indexes.
