# Enterprise Rebalance Simulation Engine (DPM)

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
pytest tests/