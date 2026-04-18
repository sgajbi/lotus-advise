# Operations Runbook

## Core runtime surfaces

- `/health`
- `/health/live`
- `/health/ready`
- `/docs`

## Operational truths

- startup validates advisory runtime persistence and proposal runtime readiness
- readiness should fail closed when persistence or runtime dependencies are unavailable
- CI includes runtime smoke and production-profile guardrail validation, not just unit proof

## Important references

- [docs/documentation/project-overview.md](../docs/documentation/project-overview.md)
- [docs/architecture/RFC-0082-upstream-contract-family-map.md](../docs/architecture/RFC-0082-upstream-contract-family-map.md)
- [docs/standards](../docs/standards)
