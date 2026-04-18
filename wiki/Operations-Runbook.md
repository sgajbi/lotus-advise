# Operations Runbook

## Core runtime surfaces

- `/health`
- `/health/live`
- `/health/ready`
- `/docs`

## Important operational checks

- verify proposal runtime persistence is reachable before trusting lifecycle endpoints
- confirm canonical upstream service URLs are configured for local and Docker runs
- treat degraded readiness as a dependency or persistence issue first, not as a UI or orchestration bug
- use repo-native smoke and guardrail commands before inventing ad hoc runtime checks

## Operational truths

- startup validates advisory runtime persistence and proposal runtime readiness
- readiness should fail closed when persistence or runtime dependencies are unavailable
- CI includes runtime smoke and production-profile guardrail validation, not just unit proof

## Important references

- [docs/documentation/project-overview.md](../docs/documentation/project-overview.md)
- [docs/architecture/RFC-0082-upstream-contract-family-map.md](../docs/architecture/RFC-0082-upstream-contract-family-map.md)
- [docs/documentation/postgres-migration-rollout-runbook.md](../docs/documentation/postgres-migration-rollout-runbook.md)
- [docs/documentation/git-branch-protection-workflow.md](../docs/documentation/git-branch-protection-workflow.md)
- [docs/standards/enterprise-readiness.md](../docs/standards/enterprise-readiness.md)
- [docs/standards/migration-contract.md](../docs/standards/migration-contract.md)
- [docs/standards/scalability-availability.md](../docs/standards/scalability-availability.md)
