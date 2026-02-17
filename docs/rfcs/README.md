# RFC Index

Standards for all current and future RFCs:
- `docs/rfcs/RFC-CONVENTIONS.md`

| RFC | Title | Status | Depends On | File |
| --- | --- | --- | --- | --- |
| RFC-0001 | Enterprise Rebalance Simulation MVP (DPM Platform) | IMPLEMENTED (With Later RFC Deltas) | - | `docs/rfcs/RFC-0001-rebalance-simulation-mvp.md` |
| RFC-0002 | Rebalance Simulation MVP Hardening & Enterprise Completeness | IMPLEMENTED (Partially, Pre-Persistence) | RFC-0001 | `docs/rfcs/RFC-0002-rebalance-simulation-mvp-hardening-enterprise-completeness.md` |
| RFC-0003 | Rebalance Simulation Contract & Engine Completion (Audit Bundle) | IMPLEMENTED | RFC-0001, RFC-0002 | `docs/rfcs/RFC-0003-contract-engine-completion.md` |
| RFC-0004 | Institutional After-State + Holdings-aware Golden Scenarios (Demo-tight, Pre-Persistence) | IMPLEMENTED | RFC-0003 | `docs/rfcs/RFC-0004-institutional-afterstate-holdings-goldens.md` |
| RFC-0005 | Institutional Tightening (Post-trade Rules, Reconciliation, Demo Pack) | IMPLEMENTED | RFC-0004 | `docs/rfcs/RFC-0005-institutional-tightening-post-trade-rules-reconciliation-demo-pack.md` |
| RFC-0006A | Pre-Persistence Hardening - Safety, After-State Completeness, Contract Consistency | IMPLEMENTED | RFC-0003, RFC-0005 | `docs/rfcs/RFC-0006A-pre-persistence-safety-afterstate.md` |
| RFC-0006B | Pre-Persistence Hardening - Rules Configurability, Dependency Fidelity & Scenario Matrix | IMPLEMENTED | RFC-0006A | `docs/rfcs/RFC-0006B-pre-persistence-rules-scenarios-demo.md` |
| RFC-0007A | Contract Tightening - Canonical Endpoint, Discriminated Intents, Valuation Policy, Universe Locking | PARTIALLY IMPLEMENTED | RFC-0006A, RFC-0006B | `docs/rfcs/RFC-0007A-contract-tightening.md` |
| RFC-0008 | Multi-Dimensional Constraints (Attribute Tagging and Group Limits) | DRAFT | RFC-0007A | `docs/rfcs/RFC-0008-multi-dimensional-constraints-attribute-tagging-group-limits.md` |
| RFC-0009 | Tax-Aware Rebalancing (HIFO and Tax Budget) | DRAFT | RFC-0008 | `docs/rfcs/RFC-0009-tax-aware-rebalancing-hifo-tax-budget.md` |
| RFC-0010 | Turnover & Transaction Cost Control | DRAFT | RFC-0007A | `docs/rfcs/RFC-0010-turnover-transaction-cost-control.md` |
| RFC-0011 | Settlement Awareness (Cash Ladder & Overdraft Protection) | DRAFT | RFC-0007A | `docs/rfcs/RFC-0011-settlement-awareness-cash-ladder-overdraft-protection.md` |
| RFC-0012 | Mathematical Optimization (Solver Integration) | DRAFT | RFC-0008 | `docs/rfcs/RFC-0012-mathematical-optimization-solver-integration.md` |
| RFC-0013 | "What-If" Analysis Mode (Multi-Scenario Simulation) | DRAFT | RFC-0003 | `docs/rfcs/RFC-0013-what-if-analysis-mode-multi-scenario-simulation.md` |
