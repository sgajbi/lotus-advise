# Enterprise Rebalance Simulation Engine (DPM)

![Version](https://img.shields.io/badge/Version-1.1.0--RFC0002-blue.svg)
![Coverage](https://img.shields.io/badge/Coverage-100%25-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Code Style](https://img.shields.io/badge/Code%20Style-Ruff-black.svg)

## Overview
The Rebalance Simulation Service is a deterministic, highly-available engine for Discretionary Portfolio Management (DPM). It provides a mathematically sound service that translates target models into executable order intents while strictly enforcing compliance rules, product shelf semantics, and cross-currency valuations.

## Key Enterprise Features (v1.1.0)
* **Idempotency:** Safe API retries backed by SHA-256 payload hashing to prevent duplicate runs.
* **Currency Truth Model:** Absolute mathematical precision resolving all asset valuations to the Portfolio Base Currency.
* **Rule Engine & Compliance:** Evaluates the simulated post-trade state against Hard constraints (e.g., `SINGLE_POSITION_MAX`) and Soft constraints (e.g., `CASH_BAND`).
* **RFC-7807 Error Handling:** Machine-readable domain errors mapped to HTTP 422 and 409.

## Documentation Links
* **Sample Request:** [docs/sample_request.json](docs/sample_request.json)
* **Sample Golden Response:** [docs/sample_response.json](docs/sample_response.json)
 

## Development & Deployment
```bash
# Testing & Linting
ruff check .
ruff format .
pytest tests/ --cov=src

# Local Server
uvicorn src.api.main:app --reload --port 8000

# Docker Deployment
docker-compose up -d --build
