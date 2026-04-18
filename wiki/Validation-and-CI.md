# Validation and CI

## Lane model

`lotus-advise` uses:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

## Local command mapping

- `make check`
  lint, typecheck, OpenAPI, no-alias, API vocabulary, unit tests
- `make ci`
  dependency health, governance, migration smoke, security audit, combined coverage, Docker build,
  Postgres runtime contracts, production-profile guardrail negatives
- `make ci-local`
  feature-lane style local proof
- `make ci-local-docker`
  Linux container parity

## Documentation contract proof

When `README.md` changes, run:

```bash
python -m pytest tests/unit/test_local_docker_runtime_contract.py -q
```

That protects the canonical local Docker upstream URL documentation.
