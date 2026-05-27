# RFC-0026 Slice 5: Source Read Model and Aggregation

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0026: Advisor Cockpit Operating Workflow |
| **Slice** | 5 - source read models and performance-safe aggregation |
| **Status** | IMPLEMENTED - PRELOADED SOURCE AGGREGATION |
| **Implemented Date** | 2026-05-27 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0026-advisor-cockpit-gold-standard` |
| **Capability Posture** | This slice implements a pure Advise core source-read-model aggregation layer. It does not expose cockpit APIs, persist action items, promote cockpit data products, add Gateway/Workbench surfaces, or claim runtime advisor-cockpit support. Those remain mandatory subsequent RFC-0026 slices. |

## Decision

Slice 5 adds `src/core/advisor_cockpit/source_read_model.py` as the bounded aggregation layer
between existing advisory source records and RFC-0026 action construction.

The module consumes preloaded source batches instead of performing repository reads in loops. That
keeps the cockpit aggregation boundary performance-safe before runtime repository/API wiring is
added:

1. proposal records are filtered to active advisory workflow states,
2. policy evaluations are filtered to `PENDING_REVIEW` and `BLOCKED`,
3. memo records produce blocked package sources only when status, finalization, or review posture
   requires attention,
4. source supportability events remain explicit source inputs,
5. unsupported capabilities remain explicit source inputs,
6. the read model returns source counts, source action inputs, and sorted `AdvisoryActionItem`
   records.

## Implemented Core Contracts

| Contract | Responsibility |
| --- | --- |
| `AdvisorCockpitSourceBatch` | Preloaded bounded source set for proposals, policy evaluations, memos, supportability events, and unsupported capabilities. |
| `AdvisorCockpitSourceReadModel` | Aggregated source posture plus sorted cockpit action items derived from the batch. |
| `build_advisor_cockpit_source_read_model` | Pure aggregation helper that maps source records to action sources and first-wave action items. |
| `ACTIVE_PROPOSAL_STATES` | Workflow states that can contribute meeting-preparation actions. |
| `COCKPIT_POLICY_REVIEW_STATUSES` | Policy postures that can contribute policy-review actions. |

## Source Mapping

| Source | Mapping |
| --- | --- |
| Active `ProposalRecord` | Creates `MeetingPreparationActionSource` for advisor-owned meeting preparation. |
| `PolicyEvaluationRecord` with `PENDING_REVIEW` | Creates a compliance-owned policy-review action source. |
| `PolicyEvaluationRecord` with `BLOCKED` | Creates a blocking compliance-owned policy-review action source. |
| `ProposalMemoRecord` with `BLOCKED` | Creates a blocked memo-package source with memo lineage hash. |
| `ProposalMemoRecord` not finalized | Creates a blocked memo-package source with `MEMO_FINALIZATION_REQUIRED`. |
| `ProposalMemoRecord` finalized but not reviewed | Creates a blocked memo-package source with `MEMO_REVIEW_REQUIRED`. |
| Completed proposal, ready policy, reviewed ready memo | Does not create a cockpit action. |

## Boundary Controls

Slice 5 keeps the runtime claim boundary unchanged:

1. no repository protocol is changed,
2. no API route is exposed,
3. no persistence table is added,
4. no acknowledgement write behavior is added,
5. no Gateway or Workbench contract is added,
6. no data product, trust telemetry, or `/platform/capabilities` claim is promoted,
7. canonical `RFC26_ADVISOR_COCKPIT_CANONICAL` proof remains blocked until backend, Gateway, and
   Workbench runtime behavior exists.

This is not deferral outside RFC-0026. It is the required source-aggregation step before the
runtime API slice can safely add bounded repository loaders, filters, pagination, entitlement
projection, OpenAPI certification, and live proof.

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Preloaded aggregation | Tests build a bounded source batch with proposals, policy evaluations, memos, supportability, and unsupported capabilities. |
| Source filtering | Tests prove ready/completed sources do not create cockpit actions. |
| Lineage preservation | Tests prove policy evaluation hashes and memo hashes are preserved in generated actions. |
| Sorted first-wave actions | Tests prove the read model returns deterministic action ordering through the Slice 4 factory. |
| Non-promoting posture | RFC/wiki tests assert Slice 5 is indexed without advertising runtime cockpit support. |

Validation:

1. `python -m pytest tests/unit/advisory/engine/test_engine_advisor_cockpit_source_read_model.py`
2. `python -m pytest tests/unit/test_rfc0026_slice5_source_read_model_contract.py`
3. `python -m ruff check .`
4. `python -m ruff format --check .`

## Next Slice Handoff

Slice 6 can now add deterministic priority, next-action, SLA aging, and acknowledgement interaction
rules over the action sources and generated action items. Runtime support remains unpromoted until
the RFC-0026 API, persistence, Gateway, Workbench, mesh, and canonical proof slices are implemented
and validated.
