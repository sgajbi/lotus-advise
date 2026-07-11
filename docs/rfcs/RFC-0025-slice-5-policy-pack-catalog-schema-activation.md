# RFC-0025 Slice 5 - Policy-Pack Catalog, Schema, And Activation Lifecycle

Status: IMPLEMENTED - CATALOG AND ACTIVATION ONLY; NO POLICY EVALUATION PROMOTED

## Scope Boundary

Slice 5 introduces the first implementation-backed RFC-0025 policy-pack catalog surface in
`lotus-advise`.

It supports:

1. `GET /advisory/policy-packs`,
2. `GET /advisory/policy-packs/{policy_pack_id}/versions/{policy_version}`,
3. `POST /advisory/policy-packs/{policy_pack_id}/versions/{policy_version}/validate`,
4. `POST /advisory/policy-packs/{policy_pack_id}/versions/{policy_version}/activate`,
5. source-controlled reference packs:
   `GLOBAL_PRIVATE_BANKING_BASELINE` and `SG_PRIVATE_BANKING_REFERENCE`,
6. canonical content hashes for immutable policy-pack versions,
7. schema/content validation with fail-fast diagnostics,
8. idempotent validation and activation events,
9. maker-checker activation where configured,
10. explicit reference-pack posture:
    `REFERENCE_EXAMPLE_NOT_LEGAL_ADVICE`.

This slice does not implement proposal policy evaluation, policy evaluation persistence, policy
review queues, compliance sign-off packages, Gateway policy consumption, Workbench policy
consumption, or client-ready publication.

## Implementation

Implementation lives in:

1. `src/core/policy_packs/catalog.py`,
2. `src/core/policy_packs/models.py`,
3. `src/api/proposals/routes_policy_packs.py`,
4. `src/api/capabilities/service.py`.

The catalog contract is `rfc0025.policy-pack-catalog.v1`.

Policy-pack versions are hash-backed with `sha256:` canonical content hashes. Activation requires
the caller to supply the validated source content hash. Activated versions cannot be reactivated
with a different command, and maker-checker packs require the activation actor to differ from the
validation actor.

Activation enforces a one-active-version invariant per `policy_pack_id`. Activating a different
validated version atomically changes that version to `ACTIVE` in the catalog snapshot and marks the
prior active version `SUPERSEDED`; the activation audit event records the previous and resulting
active versions, actor, idempotency key, request hash, and timestamp. If existing catalog state
contains more than one active version for the same pack, activation fails closed with
`POLICY_PACK_ACTIVE_VERSION_CONFLICT` until the duplicate active state is remediated. PostgreSQL
persistence backs the invariant with the `policy_packs` `0002_one_active_policy_pack_version`
migration, which installs a partial unique index on `policy_pack_id` for `ACTIVE` rows.

The `/platform/capabilities` response now advertises `advisory.policy_pack_catalog` and
`advisory_policy_pack_catalog` as catalog support only. It still does not advertise
`advisory.proposals.policy_evaluation` or `advisory_policy_evaluation`.

## Acceptance Evidence

Local behavioral proof:

1. `tests/unit/advisory/engine/test_engine_policy_pack_catalog.py`
   validates idempotent validation, idempotency conflicts, content-hash enforcement,
   maker-checker enforcement, activation immutability, one-active-version supersession,
   duplicate-active conflict behavior, and fail-fast invalid-pack diagnostics.
2. `tests/unit/advisory/api/test_api_advisory_policy_packs.py`
   validates list/detail/validate/activate routes, audit events, OpenAPI route publication, and
   absence of proposal policy-evaluation routes.
3. `tests/unit/advisory/api/test_api_integration_capabilities.py`
   validates catalog capability publication while policy evaluation remains unpromoted.

## Wiki And README Decision

Repo-local wiki source and RFC index are updated because operator-facing supported-feature truth
changed. README does not need a separate command update because repo-native commands and runtime
bring-up are unchanged.
