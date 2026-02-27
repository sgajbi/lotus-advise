# Dependency Hygiene Standard Alignment

Service: lotus-advise

This repository adopts the platform-wide standard defined in:
- `lotus-platform/Dependency Hygiene and Security Standard.md`
- `lotus-platform/Backend Foundation Standardization.md`

## Required Baseline

- No known high/critical dependency vulnerabilities are allowed.
- Dependency health must be validated in CI and before merge.
- Local and CI dependency checks should remain aligned.

## Execution Commands

- Local health check:
  - `python scripts/dependency_health_check.py --requirements requirements.txt`
- Environment dependency consistency:
  - `python -m pip check`
- CI-aligned security audit target:
  - `make security-audit`

## Update Cadence

- Patch/minor updates for tooling and low-risk libraries should be reviewed continuously.
- Runtime package major upgrades require explicit compatibility validation in unit, integration, and e2e buckets.
- Any dependency policy change must be documented in an ADR/RFC.

## Evidence

- CI job: `Lint & Dependency Checks`
- Platform conformance artifacts under `lotus-platform/output/`
