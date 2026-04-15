# RFC-0082 Upstream Contract Family Map

This document records how `lotus-advise` consumes upstream Lotus services under `lotus-platform`
RFC-0082.

`lotus-advise` owns advisory workflow, proposal simulation orchestration, proposal lifecycle state,
decision summary persistence, proposal alternatives, approval posture, consent-related workflow
behavior, and advisory execution readiness. It does not own canonical portfolio source data,
performance analytics, or risk analytics.

## Current Integration Posture

1. REST/OpenAPI remains the governed integration contract for current `lotus-advise` upstream calls.
2. No current advisory integration requires or justifies gRPC.
3. `lotus-core` remains the source-data and simulation-execution authority for advisory proposal
   context.
4. `lotus-risk` remains the risk methodology authority for advisory risk-lens enrichment.
5. `lotus-performance` is currently a readiness dependency only; `lotus-advise` does not consume
   performance analytics data as an input contract.

## `lotus-core` Contract Family Map

| Advise integration surface | Upstream route | RFC-0082 family | Advise use | Boundary rule |
| --- | --- | --- | --- | --- |
| advisory simulation execution client | `/integration/advisory/proposals/simulate-execution` | Control Execution / advisory simulation | execute proposal simulation through core-governed state and execution semantics | do not duplicate core simulation or execution readiness semantics locally |
| stateful context portfolio load | `GET /portfolios/{portfolio_id}` | Operational Read | proposal context source data | do not infer analytics conclusions from operational reads |
| stateful context positions load | `GET /portfolios/{portfolio_id}/positions` | Operational Read | holdings context for proposal construction | keep valuation and source attribution aligned to core |
| stateful context cash balance load | `POST /reporting/cash-balances/query` | Operational Read watchlist | cash context for proposal construction | preserve reporting/source methodology; do not create local cash methodology |
| stateful context instrument load | `GET /instruments/` | Operational Read | instrument reference support | source attributes remain core-owned |
| stateful context price load | `GET /prices/` | Operational Read | market price support for advisory context | price authority remains core-owned |
| stateful context FX load | `GET /fx-rates/` | Operational Read | currency conversion support for advisory context | FX authority remains core-owned |
| stateful context enrichment load | `POST /integration/instruments/enrichment-bulk` | Analytics Input watchlist | enrichment context for proposal construction | enrichment semantics remain upstream; local fallback labels are not authoritative analytics |

Environment binding:

1. `LOTUS_CORE_BASE_URL` is the lotus-core control-plane base URL for advisory simulation execution
   and control-plane enrichment routes.
2. `LOTUS_CORE_QUERY_BASE_URL` is the lotus-core query-plane base URL for operational portfolio,
   position, cash, price, instrument, and FX reads.
3. Stateful context enrichment uses the control-plane base URL for
   `/integration/instruments/enrichment-bulk`; query reads must not be reused for this route.
4. Advisory simulation must fail closed when only `LOTUS_CORE_QUERY_BASE_URL` is configured; query
   reads are not an execution authority for `/integration/advisory/proposals/simulate-execution`.

## `lotus-risk` Contract Family Map

| Advise integration surface | Upstream route | Authority | Advise use | Boundary rule |
| --- | --- | --- | --- | --- |
| risk enrichment client | `/analytics/risk/concentration` | `lotus-risk` risk analytics authority | concentration and risk-lens enrichment for proposal alternatives | no local duplicated concentration methodology or risk conclusion generation |

## `lotus-performance` Posture

`lotus-advise` currently checks `lotus-performance` dependency readiness, but it does not consume
performance analytics as proposal source data. If advisory proposal behavior later depends on
performance analytics, that dependency must be classified explicitly and should consume
`lotus-performance` as the analytics authority rather than sourcing performance conclusions from
`lotus-core` operational reads.

## Conformance Rules

1. Advisory workflows may evaluate proposal intent, suitability posture, alternatives, approvals, and
   workflow readiness.
2. Advisory workflows must not become the source of portfolio valuation, performance attribution, risk
   concentration, benchmark methodology, or reporting methodology.
3. Local fallback or derivation behavior must be bounded, explicitly supportability-oriented, and never
   presented as an authoritative replacement for core or risk output.
4. Proposal alternatives must remain anchored to canonical `lotus-core` simulation and `lotus-risk`
   enrichment.
5. New upstream source-data consumption must be classified into an RFC-0082 family before becoming a
   stable advisory contract.
6. Transport optimization discussions start with retrieval shape, payload size, caching, and upstream
   contract design. gRPC is not a default answer for advisory integration.

## Current Evidence

Existing tests that cover this posture include:

1. `tests/unit/advisory/api/test_lotus_core_stateful_context.py`
2. `tests/unit/advisory/api/test_lotus_core_simulation_client.py`
3. `tests/unit/advisory/api/test_lotus_core_runtime_config.py`
4. `tests/unit/advisory/api/test_lotus_risk_enrichment_client.py`
5. `tests/integration/advisory/api/test_proposal_api_workflow_integration.py`
6. `tests/e2e/live/test_cross_service_parity_live.py`
7. `tests/e2e/live/test_degraded_runtime_live.py`
8. `tests/e2e/live/test_live_runtime_suite.py`

This RFC-0082 documentation slice did not change runtime behavior, OpenAPI output, or upstream
request/response contracts.

## Gap Register

1. Advisory stateful context still uses multiple operational reads. If the access pattern grows into a
   bulk analytics input, prefer a governed `lotus-core` snapshot or analytics-input contract over
   additional convenience reads.
2. `/integration/advisory/proposals/simulate-execution` should remain visible in the RFC-0082 watchlist
   because it is advisory-specific control execution rather than a generic read model.
3. Enrichment fallback labels in advisory context should stay supportability-only and must not expand
   into local risk, liquidity, or suitability methodology.
4. If proposal simulation becomes latency-constrained, tune source-data shape, simulation payloads,
   caching, and upstream query design before considering a transport change.

## Validation Lane

This document is governed as Feature Lane documentation and contract proof. Escalate to PR Merge Gate
only when a future slice changes advisory runtime behavior, public API contracts, or upstream coupling.
