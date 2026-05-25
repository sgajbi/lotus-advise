# RFC-0025 Slice 2 - Cleanup and Structure Review

| Field | Value |
| --- | --- |
| **RFC** | RFC-0025: Enterprise Suitability and Best-Interest Policy Packs |
| **Slice** | 2 - Cleanup and Structure |
| **Status** | IMPLEMENTED - CURRENT POLICY/SUITABILITY BOUNDARY CLEANED; NO RUNTIME POLICY-PACK CAPABILITY PROMOTED |
| **Date** | 2026-05-26 |
| **Repository** | `lotus-advise` |

## Purpose

Slice 2 prepares the current `lotus-advise` suitability and advisory-policy context foundation for
future RFC-0025 policy-pack implementation without adding unsupported policy-pack runtime behavior.

The slice is intentionally small. It removes misleading duplicate scanner wiring and centralizes the
current advisory-policy context status checks so suitability, decision summary, and future
policy-pack code do not each interpret raw context strings differently.

## Implemented Cleanup

1. `src/core/advisory/policy_context.py` now owns the current policy-context status vocabulary and
   accessors for client, mandate, and jurisdiction availability.
2. `src/core/common/suitability.py` now consumes those accessors instead of interpreting raw
   `client_context_status` and `mandate_context_status` values locally.
3. `src/core/advisory/decision_summary.py` now uses the same accessors for client/mandate posture
   so proposal decision summaries and suitability checks share one source of truth.
4. The duplicate empty `_GLOBAL_PRIVATE_BANKING_BASELINE_PACK` definition was removed from the
   suitability scanner. The scanner now has one baseline pack wiring point.

## Deliberate Non-Changes

1. No policy-pack catalog, activation, validation, evaluation, persistence, replay, review-queue,
   sign-off-package, report-package, AI-handoff, Gateway, or Workbench runtime surface was added.
2. No empty RFC-0025 module tree was introduced. Dedicated policy modules will be created in the
   implementation slices where they carry real behavior and tests.
3. No supported-feature or `/platform/capabilities` promotion was made.
4. No legal, regulatory, or client-ready policy-content claim was introduced.

## Boundary Decision

The current pre-policy boundary is:

1. `src/core/advisory/policy_context.py` owns source-context selectors and availability posture.
2. `src/core/common/suitability.py` remains the RFC-0010/RFC-0021 suitability scanner and consumes
   policy context only as evidence availability, not as a versioned RFC-0025 policy engine.
3. Future RFC-0025 implementation slices must create dedicated modules for policy domain,
   configuration, validation, evaluation, persistence, replay, API, review-queue, sign-off-package,
   report-handoff, AI-handoff, and supportability behavior when those behaviors are implemented.

This avoids stretching the existing suitability scanner into the enterprise policy-pack engine.

## Validation

Focused validation:

1. `python -m pytest tests/unit/advisory/engine/test_engine_policy_context.py tests/unit/advisory/engine/test_engine_suitability_scanner.py tests/unit/advisory/engine/test_engine_proposal_decision_summary.py -q`
2. `python -m ruff check src/core/advisory/policy_context.py src/core/common/suitability.py src/core/advisory/decision_summary.py tests/unit/advisory/engine/test_engine_policy_context.py`

Repository-native gates and PR/mainline evidence are recorded on the RFC-0025 Slice 2 PR.

## Completion Criteria

Slice 2 is complete when:

1. the focused tests above pass,
2. the RFC/docs/wiki source records this slice as non-claiming cleanup,
3. repo-native local gates pass,
4. PR checks pass,
5. the PR is merged to `main`,
6. wiki source is published and drift is zero if wiki truth changed,
7. main releasability passes,
8. the working tree and branch posture are clean.
