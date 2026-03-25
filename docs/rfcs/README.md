# RFC Index

Standards for all current and future RFCs:
- `docs/rfcs/RFC-CONVENTIONS.md`

Governance boundary:
- Service-specific implementation RFCs belong in this repository.
- Cross-cutting platform and multi-service RFCs belong in `https://github.com/sgajbi/lotus-platform`.

This index tracks the active advisory RFC set retained in `lotus-advise` after the advisory-only
repository cleanup.

| RFC | Title | Status | Depends On | File |
| --- | --- | --- | --- | --- |
| RFC-0014A | Advisory Proposal Simulation MVP (Manual Trades + Cash Flows) | IMPLEMENTED | - | `docs/rfcs/advisory pack/refine/RFC-0014A-advisory-proposal-simulate-mvp.md` |
| RFC-0014B | Advisory Proposal Auto-Funding (FX Spot Intents + Dependency Graph) | IMPLEMENTED | RFC-0014A | `docs/rfcs/advisory pack/refine/RFC-0014B-advisory-proposal-auto-funding.md` |
| RFC-0014C | Drift Analytics for Advisory Proposals (Before vs After vs Reference Model) | IMPLEMENTED | RFC-0014A | `docs/rfcs/advisory pack/refine/RFC-0014C-drift-analytics.md` |
| RFC-0014D | Suitability Scanner v1 for Advisory Proposals | IMPLEMENTED | RFC-0014A | `docs/rfcs/advisory pack/refine/RFC-0014D-suitability-scanner-v1.md` |
| RFC-0014E | Advisory Proposal Artifact | IMPLEMENTED | RFC-0014A, RFC-0014B, RFC-0014C, RFC-0014D | `docs/rfcs/advisory pack/refine/RFC-0014E-proposal-artifact.md` |
| RFC-0014G | Proposal Persistence and Workflow Lifecycle | IMPLEMENTED | RFC-0014A, RFC-0014E, RFC-0014F | `docs/rfcs/advisory pack/refine/RFC-0014G-proposal-persistence-workflow-lifecycle.md` |
| RFC-0001 | PostgreSQL-Only Production Mode Cutover | COMPLETED | - | `docs/rfcs/RFC-0001-postgres-only-production-mode-cutover.md` |
| RFC-0002 | Automated Release Notes and Lightweight Release Process | PROPOSED | RFC-0001 | `docs/rfcs/RFC-0002-automated-release-notes-and-release-process.md` |
| RFC-0003 | Advisory Proposal Workflow Coverage Hardening (Approval Chain Paths) | IMPLEMENTED | RFC-0014G | `docs/rfcs/RFC-0003-advisory-proposal-workflow-coverage-hardening.md` |
| RFC-0004 | Iterative Advisory Proposal Workspace Contract | PROPOSED | RFC-0014G, RFC-0003 | `docs/rfcs/RFC-0004-iterative-advisory-proposal-workspace-contract.md` |
| RFC-0005 | PostgreSQL-Only Advisory Runtime Hard Cutover | PROPOSED | RFC-0001 | `docs/rfcs/RFC-0005-postgres-only-advisory-runtime-hard-cutover.md` |
| RFC-0006 | lotus-advise Target Operating Model and Integration Architecture | PROPOSED | RFC-0014G, RFC-0003, RFC-0004 | `docs/rfcs/RFC-0006-lotus-advise-target-operating-model-and-integration-architecture.md` |
| RFC-0006A | Advisory-Only Architecture Reset and Integration Seams | IMPLEMENTED | RFC-0006 | `docs/rfcs/RFC-0006A-advisory-only-architecture-reset-and-integration-seams.md` |

