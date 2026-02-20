# RFC Index

Standards for all current and future RFCs:
- `docs/rfcs/RFC-CONVENTIONS.md`

| RFC | Title | Status | Depends On | File |
| --- | --- | --- | --- | --- |
| RFC-0001 | Enterprise Rebalance Simulation MVP (DPM Platform) | IMPLEMENTED | - | `docs/rfcs/RFC-0001-rebalance-simulation-mvp.md` |
| RFC-0002 | Rebalance Simulation MVP Hardening & Enterprise Completeness | IMPLEMENTED | RFC-0001 | `docs/rfcs/RFC-0002-rebalance-simulation-mvp-hardening-enterprise-completeness.md` |
| RFC-0003 | Rebalance Simulation Contract & Engine Completion (Audit Bundle) | IMPLEMENTED | RFC-0001, RFC-0002 | `docs/rfcs/RFC-0003-contract-engine-completion.md` |
| RFC-0004 | Institutional After-State + Holdings-aware Golden Scenarios (Demo-tight, Pre-Persistence) | IMPLEMENTED | RFC-0003 | `docs/rfcs/RFC-0004-institutional-afterstate-holdings-goldens.md` |
| RFC-0005 | Institutional Tightening (Post-trade Rules, Reconciliation, Demo Pack) | IMPLEMENTED | RFC-0004 | `docs/rfcs/RFC-0005-institutional-tightening-post-trade-rules-reconciliation-demo-pack.md` |
| RFC-0006A | Pre-Persistence Hardening - Safety, After-State Completeness, Contract Consistency | IMPLEMENTED | RFC-0003, RFC-0005 | `docs/rfcs/RFC-0006A-pre-persistence-safety-afterstate.md` |
| RFC-0006B | Pre-Persistence Hardening - Rules Configurability, Dependency Fidelity & Scenario Matrix | IMPLEMENTED | RFC-0006A | `docs/rfcs/RFC-0006B-pre-persistence-rules-scenarios-demo.md` |
| RFC-0007A | Contract Tightening - Canonical Endpoint, Discriminated Intents, Valuation Policy, Universe Locking | IMPLEMENTED | RFC-0006A, RFC-0006B | `docs/rfcs/RFC-0007A-contract-tightening.md` |
| RFC-0008 | Multi-Dimensional Constraints (Attribute Tagging and Group Limits) | IMPLEMENTED | RFC-0007A | `docs/rfcs/RFC-0008-multi-dimensional-constraints-attribute-tagging-group-limits.md` |
| RFC-0009 | Tax-Aware Rebalancing (HIFO and Tax Budget) | IMPLEMENTED | RFC-0008 | `docs/rfcs/RFC-0009-tax-aware-rebalancing-hifo-tax-budget.md` |
| RFC-0010 | Turnover & Transaction Cost Control | IMPLEMENTED | RFC-0007A | `docs/rfcs/RFC-0010-turnover-transaction-cost-control.md` |
| RFC-0011 | Settlement Awareness (Cash Ladder & Overdraft Protection) | IMPLEMENTED | RFC-0007A | `docs/rfcs/RFC-0011-settlement-awareness-cash-ladder-overdraft-protection.md` |
| RFC-0012 | Mathematical Optimization (Solver Integration) | IMPLEMENTED | RFC-0008 | `docs/rfcs/RFC-0012-mathematical-optimization-solver-integration.md` |
| RFC-0013 | "What-If" Analysis Mode (Multi-Scenario Simulation) | IMPLEMENTED | RFC-0003 | `docs/rfcs/RFC-0013-what-if-analysis-mode-multi-scenario-simulation.md` |
| RFC-0014A | Advisory Proposal Simulation MVP (Manual Trades + Cash Flows) | IMPLEMENTED | RFC-0003, RFC-0006A | `docs/rfcs/advisory pack/refine/RFC-0014A-advisory-proposal-simulate-mvp.md` |
| RFC-0014B | Advisory Proposal Auto-Funding (FX Spot Intents + Dependency Graph) | IMPLEMENTED | RFC-0014A, RFC-0006A | `docs/rfcs/advisory pack/refine/RFC-0014B-advisory-proposal-auto-funding.md` |
| RFC-0014C | Drift Analytics for Advisory Proposals (Before vs After vs Reference Model) | IMPLEMENTED | RFC-0014A, RFC-0006A | `docs/rfcs/advisory pack/refine/RFC-0014C-drift-analytics.md` |
| RFC-0014D | Suitability Scanner v1 for Advisory Proposals | IMPLEMENTED | RFC-0014A, RFC-0006A | `docs/rfcs/advisory pack/refine/RFC-0014D-suitability-scanner-v1.md` |
| RFC-0014E | Advisory Proposal Artifact | IMPLEMENTED | RFC-0014A, RFC-0014B, RFC-0014C, RFC-0014D | `docs/rfcs/advisory pack/refine/RFC-0014E-proposal-artifact.md` |
| RFC-0014G | Proposal Persistence and Workflow Lifecycle | IMPLEMENTED (MVP IN-MEMORY ADAPTER) | RFC-0014A, RFC-0014E, RFC-0014F | `docs/rfcs/advisory pack/refine/RFC-0014G-proposal-persistence-workflow-lifecycle.md` |
| RFC-0015 | Deferred Scope Consolidation and Completion Backlog | DRAFT | RFC-0001..RFC-0013 | `docs/rfcs/RFC-0015-deferred-scope-consolidation-and-completion-backlog.md` |
| RFC-0016 | DPM Idempotency Replay Contract for `/rebalance/simulate` | IMPLEMENTED | RFC-0001, RFC-0002, RFC-0007A | `docs/rfcs/RFC-0016-dpm-idempotency-replay-contract.md` |
