# Troubleshooting

## README validation fails

Run:

```bash
python -m pytest tests/unit/test_local_docker_runtime_contract.py -q
```

Treat failures there as canonical local Docker URL contract drift first.

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
