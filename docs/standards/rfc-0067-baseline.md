# RFC-0067 Compliance Baseline (lotus-advise)

Date: 2026-03-02
Source of truth: `lotus-platform/rfcs/RFC-0067-centralized-api-vocabulary-inventory-and-openapi-documentation-governance.md`

## Baseline Commands

- `python -m pytest tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py -q`
- `rg -n "alias=|populate_by_name|model_dump\(by_alias=True\)|validation_alias|serialization_alias|AliasChoices" src scripts`
- `rg -n "consumerSystem|tenantId|contractVersion|sourceService|generatedAt|asOfDate|policyVersion|supportedInputModes" src docs`

## Findings

1. RFC-0067 rollout scripts were missing:
- `scripts/openapi_quality_gate.py`
- `scripts/no_alias_contract_guard.py`
- `scripts/api_vocabulary_inventory.py`

2. Make/CI gates were incomplete for RFC-0067:
- no `no-alias` gate target
- no API vocabulary gate target
- no vocabulary drift validation in standard quality flow

3. Public API contract alias usage existed in `integration_capabilities`:
- alias-based response model fields (`Field(alias="...")`)
- `populate_by_name` enabled
- alias-based query parameters (`consumerSystem`, `tenantId`)

4. Non-canonical public terms existed in docs:
- camelCase contract terms persisted in `docs/rfcs/RFC-0028-dpm-integration-capabilities-contract.md`

5. Inventory artifacts were not present:
- app-local inventory file under `docs/standards/api-vocabulary/`
- synced platform inventory file under `lotus-platform/platform-contracts/api-vocabulary/`

## Baseline Status

- OpenAPI lifecycle contract tests: pass
- RFC-0067 compliance: fail (gaps above)
