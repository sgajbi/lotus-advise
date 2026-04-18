# Troubleshooting

## README validation fails

Run:

```bash
python -m pytest tests/unit/test_local_docker_runtime_contract.py -q
```

Treat failures there as canonical local Docker URL contract drift first.

## OpenAPI-facing contract docs fail validation

Run:

```bash
python -m pytest tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py -q
```

Treat failures there as schema discoverability or contract-doc drift first.

## API vocabulary file changed after `make check`

Inspect the diff before keeping it. If the only change is `generatedAt`, revert it for docs-only
slices.

## Readiness fails

Check:

- proposal runtime persistence
- advisory runtime readiness
- configured upstream service URLs

## Stateful advisory behavior looks wrong

Check:

- `LOTUS_CORE_BASE_URL`
- `LOTUS_CORE_QUERY_BASE_URL`
- `LOTUS_RISK_BASE_URL`
- RFC-0082 boundary assumptions before changing local behavior
