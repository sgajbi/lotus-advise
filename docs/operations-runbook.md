# Lotus Advise Operations Runbook

## Local Validation

- `make check`: local Feature Lane parity for lint, typecheck, OpenAPI, vocabulary, data-product,
  and unit-test gates.
- `make ci-local`: local PR Merge Gate subset without Docker, including quality-baseline
  freshness.
- `make quality-baseline`: regenerate report-only quality artifacts in `quality/`.
- `make engineering-health`: regenerate the structural engineering-health baseline.

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
