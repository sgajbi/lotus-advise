# RFC-0026 Slice 3: Data Product and Platform Hardening

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0026: Advisor Cockpit Operating Workflow |
| **Slice** | 3 - data product and platform hardening |
| **Status** | IMPLEMENTED - NON-PROMOTING DATA-PRODUCT POSTURE |
| **Implemented Date** | 2026-05-27 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0026-advisor-cockpit-gold-standard` |
| **Capability Posture** | This slice intentionally does not declare `AdvisorCockpitOperatingSnapshot:v1` or `AdvisoryActionItemRegister:v1` as active data products. Those declarations are mandatory RFC-0026 work only after runtime cockpit APIs, source-backed action construction, acknowledgement behavior, Gateway/Workbench consumption, trust telemetry, `/platform/capabilities`, and canonical live proof exist. |

## Decision

The correct gold-standard posture for Slice 3 is non-promotion.

RFC-0026 now has a dedicated cockpit core package, but it does not yet have runtime APIs,
persistence, source aggregation, trust telemetry, Gateway/Workbench consumers, or canonical proof.
Promoting cockpit products now would create an unsupported mesh claim. Therefore:

1. `contracts/domain-data-products/lotus-advise-products.v1.json` must not contain
   `AdvisorCockpitOperatingSnapshot` yet,
2. `contracts/domain-data-products/lotus-advise-products.v1.json` must not contain
   `AdvisoryActionItemRegister` yet,
3. `contracts/trust-telemetry/` must not contain cockpit telemetry snapshots yet,
4. `/platform/capabilities` must not advertise an advisor cockpit feature yet,
5. wiki and supported-features wording must remain non-promoting,
6. subsequent RFC-0026 runtime slices must add the declarations and telemetry in the same slice
   that makes the product real enough to validate.

This is not deferral outside RFC-0026. It is an implementation gate inside RFC-0026: the data
products are mandatory, but their promotion is blocked until implementation evidence exists.

## Promotion Requirements for Subsequent RFC-0026 Slices

`AdvisorCockpitOperatingSnapshot:v1` may be promoted only after:

1. snapshot API exists and is OpenAPI-certified,
2. caller-context entitlement projection is server-side and tested,
3. snapshot counts, top-priority actions, source-readiness gaps, dependency readiness, unsupported
   capabilities, and lineage refs are source-backed,
4. Gateway preserves the Advise-owned cockpit contract,
5. Workbench consumes Gateway/BFF only,
6. trust telemetry, SLO/access/evidence policy, `/platform/capabilities`, and mesh catalog
   evidence are aligned,
7. canonical `RFC26_ADVISOR_COCKPIT_CANONICAL` proof passes and is reviewed.

`AdvisoryActionItemRegister:v1` may be promoted only after:

1. action-list API exists with cursor pagination, default page size 25, maximum page size 100, and
   stable ordering,
2. action-detail API returns evidence refs, owner boundaries, lineage refs, dependency readiness,
   and source-readiness gaps,
3. acknowledgement writes are idempotent, audited, and stale-version protected,
4. action families cover the first-wave RFC-0026 required set,
5. entitlement projection is tested for advisor, desk head, compliance reviewer, operations, and
   demo/read-only contexts,
6. Gateway and Workbench preserve priorities, statuses, reason codes, owner roles, and pagination,
7. live validation defects are covered by lower-layer tests before closure.

## Platform Hardening Assessment

Existing platform and repo-native controls remain sufficient for Slice 3:

1. `make domain-data-products-gate` validates repo-native declarations against platform contracts,
2. trust telemetry validation already checks active declarations against telemetry snapshots,
3. `/platform/capabilities` tests prevent unsupported feature promotion,
4. RFC/wiki documentation contract tests protect non-promoting posture,
5. canonical front-office runtime validation is already governed and will be extended only when
   runtime behavior exists.

No `lotus-platform` code change is required for this slice. If later runtime implementation finds a
repeatable mesh, telemetry, capability, or canonical proof gap, that fix remains mandatory inside
RFC-0026 and must land in the owning repository with tests.

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| No premature declarations | Tests assert `AdvisorCockpitOperatingSnapshot` and `AdvisoryActionItemRegister` are absent from active repo-native product declarations. |
| No premature trust telemetry | Tests assert no cockpit trust telemetry snapshot exists before runtime data products are real. |
| No premature capabilities | Tests assert `/platform/capabilities` does not advertise advisor cockpit support yet. |
| Promotion requirements documented | This slice records the required runtime, Gateway, Workbench, telemetry, capabilities, mesh, and canonical proof gates. |
| Platform hardening decision | Existing platform controls are sufficient; no platform code change is needed in this slice. |

Validation:

1. `python -m pytest tests/unit/test_rfc0026_slice3_data_product_posture_contract.py`
2. `python -m pytest tests/unit/scripts/test_validate_domain_data_product_declarations.py`
3. `python -m pytest tests/unit/advisory/api/test_api_integration_capabilities.py`
4. `python -m ruff check .`
5. `python -m ruff format --check .`

## Next Slice Handoff

Slice 4 can now add first-wave action-family construction and vocabulary behavior on top of the
dedicated cockpit core package. Data-product promotion remains blocked until runtime APIs, source
aggregation, Gateway/Workbench, and canonical evidence exist.
