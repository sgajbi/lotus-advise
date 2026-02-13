# Rebalance Simulation Engine (DPM)

## Overview
The Rebalance Simulation Service is a deterministic engine for Discretionary Portfolio Management (DPM). Given a portfolio snapshot and mandate context, it produces an auditable, explainable trade plan (Order Intents) and a simulated after-state. 

This service operates strictly as a **simulation engine** with zero execution side-effects.

## Documentation
* [RFC-0001: Enterprise Rebalance Simulation MVP](docs/rfcs/RFC-0001-rebalance-simulation-mvp.md)

## Tech Stack
* **Language:** Python 3.11+
* **API Framework:** FastAPI
* **Testing:** Pytest

## Development Setup
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

```

## Running the Tests

We maintain a suite of unit tests for edge cases and deterministic "Golden Scenarios" for regression testing.

```bash
pytest tests/ -v

```

## Running the API Server

Start the local ASGI server:

```bash
uvicorn src.api.main:app --reload --port 8000

```

Once running, access the interactive API documentation at: **[http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)**


## Docker Deployment (Local & Dev)
To run the application in a production-like containerized environment:
```bash
# Build and start the container
docker-compose up --build

# Run in detached mode (background)
docker-compose up -d --build

# Stop the container
docker-compose down
Once the container is running, the API is accessible at: http://localhost:8000/docs
