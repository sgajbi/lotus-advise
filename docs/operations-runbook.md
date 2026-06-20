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

## Operational Posture

- Treat GitHub Actions as CI truth.
- Treat `quality/` reports as baseline evidence, not production-readiness signoff.
- Publish wiki only when repo-local `wiki/` source changes.
