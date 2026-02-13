 
#  Rebalance Simulation Engine (DPM)

![CI Pipeline](https://github.com/workflows/ci.yml/badge.svg)
![Coverage](https://img.shields.io/badge/Coverage-100%25-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Code Style](https://img.shields.io/badge/Code%20Style-Ruff-black.svg)

## Overview
The Rebalance Simulation Service is a deterministic engine for Discretionary Portfolio Management (DPM). [cite_start]It provides a deterministic, auditable service that, given a portfolio snapshot and mandate context, produces a simulated after-state and order intents[cite: 2]. 

[cite_start]This service operates strictly as a **simulation engine** with zero execution side-effects[cite: 3]. [cite_start]It translates targets into order intents, handling FX funding and dependency grouping[cite: 6].

## Documentation
* **RFC:** [RFC-0001: Enterprise Rebalance Simulation MVP](docs/rfcs/RFC-0001-rebalance-simulation-mvp.md)
* **Sample Payload:** [docs/sample_request.json](docs/sample_request.json)


## Tech Stack
* **Language:** Python 3.11+
* **API Framework:** FastAPI
* **Testing:** Pytest & Pytest-Cov (100% enforced)
* **Linting & Formatting:** Ruff
* **Deployment:** Docker & Docker Compose

## Development Setup
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

```

## Testing & Quality Assurance

We maintain a strict 100% test coverage requirement. CI will fail if coverage drops or if linting fails.

**Run the Linter & Formatter (Ruff):**

```bash
ruff check . --fix
ruff format .

```

**Run the Test Suite (Pytest):**

```bash
pytest tests/ --cov=src --cov-report=term-missing

```

## Local API Server (FastAPI)

Start the local ASGI server:

```bash
uvicorn src.api.main:app --reload --port 8000

```

Interactive API docs: **[http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)**

## Docker Deployment (Local & Dev)

To run the application in an isolated, production-like container:

```bash
# Build and start the container
docker-compose up --build

# Run in detached mode (background)
docker-compose up -d --build

# Stop the container
docker-compose down