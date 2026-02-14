# DPM Rebalance Engine: Demo Scenarios

This directory contains curated JSON input files demonstrating the engine's capabilities and safety features.

## Scenarios

### 1. Simple Drift (`01_simple_drift.json`)
* **Goal:** Rebalance a portfolio that has drifted from its model.
* **Key Features:**
    * Generates `SECURITY_TRADE` intents (Sell Overweight / Buy Underweight).
    * Full `after_simulated` state with allocations.
    * Rule Engine output (`CASH_BAND`, `SINGLE_POSITION_MAX`).

### 2. Safety Block (`02_safety_block.json`)
* **Goal:** Demonstrate the "Institution-Grade" safety guardrails (RFC-0005).
* **Context:** A request attempts to sell 2000 units of an asset where only 1000 are held (Logic/Data error).
* **Outcome:**
    * Status: `BLOCKED`.
    * Diagnostic: `SIMULATION_SAFETY_CHECK_FAILED`.
    * No trades executed in reality (simulation blocked).

## Usage

You can feed these JSONs into the API endpoint `/v1/rebalance`:

```bash
curl -X POST "http://localhost:8000/v1/rebalance" \
     -H "Content-Type: application/json" \
     -d @docs/demo/01_simple_drift.json