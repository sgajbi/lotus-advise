# RFC-0021 Slice 6 Evidence: Material Change and Approval Requirement Classifiers

- RFC: `docs/rfcs/RFC-0021-proposal-decision-summary-and-enterprise-suitability-policy.md`
- Slice Status: IMPLEMENTED
- Date: 2026-04-12
- Owner: `lotus-advise`

## Scope Delivered

Slice 6 upgraded the decision-summary projector from a status-and-missing-evidence view into a reusable advisory change-and-requirement classifier layer.

Implemented outcomes:

1. extracted approval-requirement projection into a dedicated classifier module,
2. extracted material-change projection into a dedicated classifier module,
3. classified deterministic material changes across asset allocation, cash, currency exposure, concentration, product complexity, mandate alignment, data quality, and approval posture,
4. strengthened approval requirements so suitability-driven remediation and mandate exceptions are represented explicitly instead of relying only on gate-level routing,
5. kept `decision_summary.py` as an orchestrator rather than allowing it to accumulate more mixed policy logic.

## Code Changes

### Approval Requirement Classifier

`src/core/advisory/decision_requirements.py`

Added a reusable classifier that consolidates:

1. gate-driven review requirements,
2. blocking missing-evidence remediation requirements,
3. suitability issue approval implications.

New behavior:

1. suitability issues with `approval_implication = RISK_REVIEW` or `COMPLIANCE_REVIEW` now surface as explicit approval requirements,
2. client-context evidence gaps map to `DATA_REMEDIATION`,
3. restricted-product mandate evidence gaps map to `MANDATE_EXCEPTION_APPROVAL`,
4. duplicate requirements are merged deterministically instead of emitted multiple times.

### Material Change Classifier

`src/core/advisory/decision_material_changes.py`

Added a reusable material-change classifier for the decision summary.

Material change families now projected from real evidence:

1. `ALLOCATION_CHANGE`,
2. `CASH_CHANGE`,
3. `CURRENCY_EXPOSURE_CHANGE`,
4. `CONCENTRATION_CHANGE`,
5. `PRODUCT_COMPLEXITY_CHANGE`,
6. `MANDATE_ALIGNMENT_CHANGE`,
7. `DATA_QUALITY_CHANGE`,
8. `APPROVAL_REQUIREMENT_CHANGE`.

Decision:

1. the classifier intentionally uses a focused set of enterprise-relevant thresholds,
2. it does not attempt to emit a generic “diff everything” log,
3. every change family is backed by existing canonical proposal evidence.

### Decision Summary Orchestration

`src/core/advisory/decision_summary.py`

Refactored the summary builder to compose:

1. missing-evidence projection,
2. approval-requirement projection,
3. material-change projection.

Result:

1. the module is smaller and easier to extend,
2. approval logic and change classification are now independently testable,
3. later slices can add live validation and operator evidence without reopening one large decision-policy file.

## Tests Added Or Tightened

### Decision Summary Classifier Coverage

`tests/unit/advisory/engine/test_engine_proposal_decision_summary.py`

Added targeted scenarios proving:

1. a no-op ready proposal emits no material changes,
2. cross-currency trades emit `CURRENCY_EXPOSURE_CHANGE`,
3. risk-lens deterioration emits `CONCENTRATION_CHANGE`,
4. compliance and risk review paths emit `APPROVAL_REQUIREMENT_CHANGE`,
5. restricted-product mandate gaps emit `MANDATE_ALIGNMENT_CHANGE`,
6. mandate exception requirements are surfaced explicitly.

### Persisted Proposal Version Coverage

`tests/unit/advisory/engine/test_engine_proposal_workflow_service.py`

Added a persistence scenario proving that a stored proposal version carries the same material-change classification used by the runtime decision summary.

## Validation

Targeted slice validation:

```powershell
python -m pytest tests/unit/advisory/engine/test_engine_proposal_decision_summary.py tests/unit/advisory/engine/test_engine_proposal_workflow_service.py -q
```

Result:

1. `47` targeted tests passed.

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
6. all unit tests passed.

## Review Pass

The post-implementation review focused on whether the new material-change classifier was too broad or too coupled to artifact logic.

Decision:

1. keep decision-summary change classification separate from artifact presentation helpers,
2. reuse existing before/after/risk/suitability evidence rather than building another delta model,
3. keep thresholds narrow and explicit so the decision summary stays readable for advisors.

## Remaining Work For Next Slice

Slice 7 should validate the enriched decision summary in live and operator-facing evidence paths.

Immediate next focus:

1. live validation for ready, blocked, review, and insufficient-evidence decision outcomes,
2. operator-facing evidence that proves material changes and approval requirements are present on canonical runtime flows,
3. final documentation, context assessment, and branch hygiene in the closing slice.
