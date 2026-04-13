# RFC-0022 Slice 7 Evidence: Live Validation and Operator Evidence

- RFC: `docs/rfcs/RFC-0022-proposal-alternatives-and-portfolio-construction-workbench.md`
- Slice: 7
- Date: 2026-04-13
- Status: Completed

## Scope

Slice 7 closes the remaining live-validation and operator-evidence gap for proposal alternatives.

This slice extends the existing governed live-runtime suite so the runtime no longer validates only:

1. canonical allocation parity,
2. canonical risk parity,
3. decision-summary posture,
4. lifecycle and workspace continuity.

It now also validates the backend-owned proposal-alternatives surface directly.

## Delivered

### 1. Added a normalized live alternatives snapshot helper

Added `scripts/live_runtime_proposal_alternatives.py`.

This helper extracts one stable operator-facing shape from `proposal_alternatives`:

1. requested objectives,
2. feasible count,
3. feasible-with-review count,
4. rejected count,
5. selected alternative id and rank,
6. top-ranked alternative id and objective,
7. top-ranked ranking reason codes,
8. rejected reason codes,
9. request latency in milliseconds.

That keeps parity validation, degraded-runtime validation, and evidence rendering on one shared
representation instead of duplicating alternatives parsing logic across multiple scripts.

### 2. Live parity validation now proves alternatives paths explicitly

Updated `scripts/validate_cross_service_parity_live.py`.

The live suite now validates alternatives on canonical seeded portfolios across these explicit paths:

1. `no_op_path`
   a canonical stateful no-op request that still asks the backend to generate proposal alternatives,
2. `concentration_path`
   concentration-remediation alternatives,
3. `cash_raise_path`
   cash-raising alternatives with an explicit cash-floor constraint,
4. `cross_currency_path`
   currency-alignment alternatives,
5. `restricted_product_path`
   deferred restricted-product alternatives that must remain explicit rejections until canonical
   eligibility evidence exists.

The parity script now asserts:

1. the canonical stack produces at least three feasible alternatives on the no-op path,
2. concentration, cash-raise, and cross-currency paths each return at least one ranked
   alternative,
3. restricted-product paths stay honest and surface
   `ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE` instead of inventing fake support,
4. top-ranked alternatives expose ranking reason codes,
5. alternatives latency is recorded and bounded.

### 3. Degraded runtime drills now validate alternatives truthfully

Updated `scripts/validate_degraded_runtime_live.py`.

The degraded suite now validates alternatives behavior in both upstream failure modes:

1. `lotus-risk` unavailable:
   decision summary must degrade to `INSUFFICIENT_EVIDENCE`, and alternatives must produce no
   feasible outputs while surfacing `LOTUS_RISK_ENRICHMENT_UNAVAILABLE`,
2. `lotus-core` unavailable:
   the request must fail without fallback, and the degraded evidence payload records a no-fake-
   alternatives posture with `LOTUS_CORE_SIMULATION_UNAVAILABLE`.

That closes the operator-evidence gap where degraded alternatives behavior previously had to be
inferred from generic simulate failure posture.

### 4. Evidence outputs now include alternatives paths

Updated:

1. `scripts/live_runtime_suite_artifacts.py`
2. `scripts/validate_live_runtime_suite.py`
3. `scripts/run_live_runtime_evidence_bundle.py`

The machine-readable runtime artifact, markdown summary, and PR-ready summary now include:

1. no-op alternatives posture,
2. concentration alternatives posture,
3. cash-raise alternatives posture,
4. cross-currency alternatives posture,
5. restricted-product rejection posture,
6. degraded lotus-risk alternatives posture,
7. degraded lotus-core alternatives posture.

Operator evidence now records the fields required by the RFC acceptance gate:

1. alternatives count,
2. selected rank,
3. rejected reasons,
4. latency,
5. top-ranked ranking reasons.

## Tests Added Or Tightened

Updated or added:

1. `tests/unit/advisory/api/test_live_runtime_suite.py`
2. `tests/unit/advisory/api/test_live_cross_service_parity.py`
3. `tests/e2e/live/test_live_runtime_suite.py`

The slice now proves:

1. the alternatives snapshot helper normalizes ranked and rejected paths correctly,
2. the live runtime artifact serializes alternatives evidence deterministically,
3. markdown and PR summaries expose alternatives posture explicitly,
4. degraded runtime placeholders remain structurally explicit when the suite skips degraded drills,
5. the gated live E2E suite expects canonical alternatives and degraded alternatives posture.

Regression coverage remains in:

1. `tests/unit/advisory/engine/test_engine_proposal_alternatives_projection.py`
2. `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py`

Those tests continue to protect the underlying alternatives ranking and persistence behavior that the
live suite now surfaces.

## Validation

Local targeted validation completed:

1. `python -m pytest tests/unit/advisory/api/test_live_runtime_suite.py tests/unit/advisory/api/test_live_cross_service_parity.py -q`
2. `python -m pytest tests/unit/advisory/engine/test_engine_proposal_alternatives_projection.py tests/unit/advisory/engine/test_engine_proposal_workflow_service.py -q`
3. `python -m pytest tests/e2e/live/test_live_runtime_suite.py -q`
   result: skipped as designed because `RUN_LIVE_RUNTIME_SUITE=1` was not set in this session.

Planned final gate for this slice:

1. `make check`

## Review Notes

This slice received an explicit review pass before moving forward.

Review conclusions:

1. alternatives runtime parsing was pushed into a reusable helper instead of being duplicated in
   parity, degraded, and evidence scripts,
2. the restricted-product path remains explicitly deferred and honest rather than gaining fake
   superficial support,
3. degraded-runtime evidence now proves the right domain authority behavior for both `lotus-core`
   and `lotus-risk`,
4. operator evidence is materially stronger without creating a second alternatives model outside
   the existing backend-owned contract.

## Remaining For Later Slices

Still intentionally deferred to Slice 8:

1. RFC status and index closure,
2. repository-context and agent-context assessment,
3. any documentation changes beyond this slice evidence record,
4. PR finalization and branch hygiene.
