# RFC-0021 Slice 5 Evidence: Client, Mandate, and Product Context Integration

- RFC: `docs/rfcs/RFC-0021-proposal-decision-summary-and-enterprise-suitability-policy.md`
- Slice Status: IMPLEMENTED
- Date: 2026-04-12
- Owner: `lotus-advise`

## Scope Delivered

Slice 5 integrated normalized policy context into advisory simulation, suitability evaluation, decision-summary projection, workspace reevaluation, and persisted proposal lifecycle evidence.

Implemented outcomes:

1. added a reusable `advisory_policy_context` contract derived from authoritative stateful selectors,
2. propagated client, mandate, jurisdiction, and benchmark context through simulation and persisted evidence surfaces,
3. made complex-product recommendations context-aware so available household context suppresses false missing-evidence posture,
4. introduced restricted-product mandate-context evidence handling without inventing a second client or mandate authority inside `lotus-advise`,
5. replaced the decision-summary `client_and_mandate_posture` stub with a real projection backed by persisted context evidence,
6. tightened decision-summary precedence so blocking evidence gaps win over generic review routing.

## Code Changes

### Reusable Policy Context Contract

`src/core/advisory/policy_context.py`

Added a dedicated normalization module for advisory policy selectors and policy-context projection.

Result:

1. context semantics are defined once,
2. simulate, lifecycle, workspace, and replay surfaces all reuse the same contract,
3. future slices can extend the context layer without scattering policy mapping logic across services.

### Stateful Resolution And Persistence Alignment

`src/core/proposals/context.py`
`src/core/proposals/service.py`
`src/api/services/advisory_simulation_service.py`
`src/api/services/workspace_service.py`

Added `policy_selectors` to resolved context models and emitted `advisory_policy_context` inside `context_resolution` evidence.

Result:

1. stateful household and mandate identifiers now flow into the same evidence shape across transient and persisted proposal paths,
2. proposal create/version and workspace handoff no longer infer policy context independently,
3. persisted proposal evidence remains consistent with what the live simulation and workspace surfaces return.

### Suitability Context Integration

`src/core/common/suitability.py`
`src/core/advisory_engine.py`
`src/core/advisory/orchestration.py`

Extended suitability evaluation to consume normalized policy context and added one new enterprise missing-evidence path:

1. complex-product missing client-context evidence is suppressed when client context is already available,
2. restricted-product buy attempts without mandate context emit `MISSING_MANDATE_RESTRICTED_PRODUCT_EVIDENCE`,
3. policy context is attached to the explanation payload before decision-summary projection.

Result:

1. suitability behavior now reflects actual context availability instead of static product rules,
2. restricted-product workflows ask for the missing mandate evidence explicitly,
3. the same policy context drives both suitability classification and advisor-facing decision output.

### Decision Summary Tightening

`src/core/advisory/decision_summary.py`

Replaced the placeholder client/mandate posture with a real projection and tightened missing-evidence precedence.

Result:

1. proposals with full context now project `client_and_mandate_posture = AVAILABLE`,
2. partial context projects `PARTIAL` instead of a static not-integrated message,
3. blocking context gaps now produce `INSUFFICIENT_EVIDENCE` ahead of generic compliance-review wording,
4. advisor next-action routing now maps enterprise context gaps to `REQUEST_CLIENT_CONTEXT` or `REQUEST_MANDATE_CONTEXT`.

## Tests Added Or Tightened

### Shared Stateful Fixture

`tests/shared/stateful_context_builders.py`

Extended the reusable stateful-context builder to support proposal trades and cash flows so richer stateful policy scenarios can be exercised without one-off test payloads.

### Suitability Engine

`tests/unit/advisory/engine/test_engine_suitability_scanner.py`

Added a targeted scenario proving complex-product missing-evidence posture is suppressed when client context is available.

### Decision Summary

`tests/unit/advisory/engine/test_engine_proposal_decision_summary.py`

Added a projection test proving the client and mandate posture becomes `AVAILABLE` when policy context is attached.

### Simulation API

`tests/unit/advisory/api/test_api_advisory_proposal_simulate.py`

Added stateful API scenarios proving:

1. full client and mandate context avoids false complex-product evidence gaps,
2. restricted-product proposals without mandate context emit `INSUFFICIENT_EVIDENCE`,
3. the advisor next action becomes `REQUEST_MANDATE_CONTEXT`.

### Persisted Proposal Lifecycle

`tests/unit/advisory/engine/test_engine_proposal_workflow_service.py`

Added a stateful create scenario proving persisted proposal versions store the normalized policy context and project `client_and_mandate_posture = AVAILABLE`.

## Validation

Targeted slice validation:

```powershell
python -m pytest tests/unit/advisory/engine/test_engine_suitability_scanner.py tests/unit/advisory/engine/test_engine_proposal_decision_summary.py tests/unit/advisory/api/test_api_advisory_proposal_simulate.py tests/unit/advisory/engine/test_engine_proposal_workflow_service.py -q
```

Result:

1. `78` targeted tests passed.

Full repository gate:

```powershell
make check
```

Result:

1. lint passed,
2. format passed,
3. mypy passed,
4. OpenAPI gate passed,
5. vocabulary inventory passed,
6. all `477` unit tests passed.

## Review Pass

The post-implementation review focused on whether Slice 5 introduced fake authority or duplicated advisory-owned client models.

Decision:

1. keep `lotus-advise` identifier-driven for client and mandate context rather than inventing a parallel client profile schema,
2. bind missing client context to complex-product recommendations and missing mandate context to restricted-product recommendations, because those are the strongest current enterprise control points,
3. normalize policy context once in `context_resolution` evidence and reuse it everywhere instead of letting each service project its own partial posture.

## Remaining Work For Next Slice

Slice 6 should classify material changes and approval requirements from the now-stabilized decision and suitability evidence spine.

Immediate next focus:

1. material-change classification across allocation, concentration, currency, liquidity, cash, and product complexity,
2. approval-requirement projection aligned with workflow gates,
3. stronger persisted delivery-summary evidence for downstream operator and UI consumers.
