# Getting Started

## Key Commands

- `make install`
- `make check`
- `make ci`
- `make ci-local-docker`
- `make run`

## Local Expectations

`lotus-advise` expects canonical upstream integrations to be explicit during local Docker validation:

- `LOTUS_CORE_BASE_URL`
- `LOTUS_CORE_QUERY_BASE_URL`
- `LOTUS_RISK_BASE_URL`
- `LOTUS_RISK_TIMEOUT_SECONDS`
- `LOTUS_RISK_RETRY_ATTEMPTS`
- `LOTUS_RISK_RETRY_BACKOFF_SECONDS`

These bindings keep proposal simulation and advisory risk-lens behavior aligned to the actual upstream authorities instead of local stand-ins.
Lotus Risk enrichment retries transient `5xx`, `429`, and network failures with bounded operator
configuration: retry attempts default to `2` and cap at `5`, while retry backoff defaults to `0.1`
seconds and caps at `2.0` seconds.

## API Discovery

Once the service is running:

- OpenAPI UI: `/docs`
- health: `/health`
- liveness: `/health/live`
- readiness: `/health/ready`

## Demo Scenarios

The repository includes grounded demo payloads under `docs/demo/`.

Representative flows:

- proposal simulation via `POST /advisory/proposals/simulate`
- artifact generation via `POST /advisory/proposals/artifact`
- persisted proposal creation via `POST /advisory/proposals`

The demo set also covers:

- auto-funding
- blocked FX cases
- drift analytics
- suitability outcomes
- artifact generation
- lifecycle transitions
- client consent and compliance approval
- execution-ready and executed state progression
