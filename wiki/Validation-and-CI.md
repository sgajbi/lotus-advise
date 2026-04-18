# Validation and CI

## Local Commands

- `make check`
- `make ci`
- `make ci-local-docker`

## Validation Intent

The repository uses a layered validation posture:

- fast local quality checks
- PR-grade local validation
- Linux container parity for host-side CI expectations

## What The Repository Explicitly Governs

Current repository context and README make these expectations explicit:

- project-scoped dependency health
- coverage
- Docker build
- Postgres runtime smoke
- production-profile guardrail validation
- OpenAPI and vocabulary governance
- no-alias contract discipline
- upstream contract-family discipline for advisory dependencies

## Merge Hygiene

The repository follows the platform workflow model:

1. branch from `main`
2. keep one branch per RFC or slice
3. use PR-first delivery
4. merge with green required checks
5. return to `local = remote = main`

## Documentation Validation Lane

Wiki and documentation updates are Feature Lane work unless they change:

- runtime behavior
- public API contracts
- upstream coupling

Those cases should be treated as PR Merge Gate material because they alter service truth rather than only describing it.
