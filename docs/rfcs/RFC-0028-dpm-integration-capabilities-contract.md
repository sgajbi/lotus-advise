# RFC-0028 lotus-advise Integration Capabilities Contract

- Status: Accepted
- Date: 2026-02-23

## Summary

Add `GET /platform/capabilities` to expose backend-governed lotus-advise feature and workflow capability flags for lotus-gateway, lotus-core, and UI integration.

## Contract

Inputs:
- `consumer_system`
- `tenant_id`

Outputs:
- `contract_version`
- `source_service`
- `consumer_system`
- `tenant_id`
- `policy_version`
- `supported_input_modes`
- `features[]`
- `workflows[]`

## Rationale

1. Keeps workflow/feature control in backend.
2. Enables lotus-gateway/UI to drive behavior from capability contracts.
3. Aligns lotus-advise with lotus-core and lotus-performance integration-governance direction.
