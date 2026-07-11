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
- camelCase contract terms persisted in older advisory capability documentation before RFC-0067 cleanup

5. Inventory artifacts were not present:
- app-local inventory file under `docs/standards/api-vocabulary/`
- synced platform inventory file under `lotus-platform/platform-contracts/api-vocabulary/`

## Baseline Status

- OpenAPI lifecycle contract tests: pass
- RFC-0067 compliance: fail (gaps above)

## Migration Decisions

### Advisor Cockpit Caller Role Vocabulary

- Date: 2026-07-11
- Decision: `PORTFOLIO_MANAGER` is the canonical public caller and owner role for
  portfolio-management owned Advisor Cockpit actions.
- Compatibility posture: the legacy `DPM_OWNER` caller role is retired from public OpenAPI,
  generated API vocabulary, and runtime query validation. Requests that submit `DPM_OWNER` fail at
  the request DTO boundary instead of being translated inside the canonical contract.
- Guardrail: `scripts/no_alias_contract_guard.py` fails if `DPM_OWNER` is reintroduced into
  `src/` public contract code.
- Historical audit posture: prior ledger and RFC audit references to `DPM_OWNER` remain historical
  evidence only; no internal historical audit records are renamed without a separate migration plan.

### API Vocabulary Example Quality

- Date: 2026-07-11
- Decision: generated API vocabulary examples must be source-authored or derived from a governed
  deterministic fallback policy. Placeholder-shaped examples are not valid public contract truth.
- Blocked patterns: `sample_text`, `sample_key`, `STANDARD_TEXT`, `STANDARD_ITEM`, `ENTITY_001`,
  and generated `example_*` strings.
- Guardrail: `scripts/api_vocabulary_inventory.py --validate-only` recursively rejects placeholder
  examples in the attribute and controls catalogs and fails on inventory drift.
- Consumer posture: public examples should use representative private-banking identifiers,
  source-system values, dates, hashes, money/rate values, enums, and object/list shapes without
  publishing real customer data.

### OpenAPI Display Enrichment Versus Contract Quality

- Date: 2026-07-11
- Decision: Swagger/OpenAPI display enrichment may add readable defaults, but generated operation
  summaries, generated operation descriptions, inferred tags, and generic default error responses
  do not satisfy the OpenAPI quality gate for public routes.
- Blocked patterns: summaries shaped as `GET /path`, descriptions shaped as
  `GET operation for /path in lotus-advise.`, inferred public tags, and generic
  `Unexpected error response.` defaults.
- Guardrail: `scripts/openapi_quality_gate.py` treats those generated values as missing contract
  documentation while allowing health/metrics infrastructure endpoints to avoid noisy artificial
  error-response requirements.
- Consumer posture: public routes must author meaningful summaries, descriptions, tags, and
  response metadata in route source or response-metadata modules.
