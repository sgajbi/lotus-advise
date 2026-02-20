# Demo Pack Manual Validation - 2026-02-20

## Scope

Validated the end-to-end demo pack scenarios through live API calls in both runtime modes:

- `uvicorn` local process on `http://127.0.0.1:8001`
- Docker Compose service on `http://127.0.0.1:8000`

Coverage includes:

- DPM simulate demos (`01`-`08`)
- DPM batch analyze demo (`09`)
- DPM async batch analyze demo (`26`)
- DPM supportability + deterministic artifact flow demo (`27`)
- DPM async manual-execute guard demo (`28`)
- DPM workflow gate default-disabled contract demo (`29`)
- Advisory simulate demos (`10`-`18`)
- Advisory artifact demo (`19`)
- Advisory lifecycle flow demos (`20`-`25`)
- Proposal list support endpoint validation

## Commands Executed

### 1) Start uvicorn (local runtime)

```powershell
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","src.api.main:app","--host","127.0.0.1","--port","8001" -PassThru
```

### 2) Validate demo pack against uvicorn

```powershell
.venv\Scripts\python scripts/run_demo_pack_live.py --base-url http://127.0.0.1:8001
```

Observed result:

```text
Demo pack validation passed for http://127.0.0.1:8001
```

### 3) Build and run Docker runtime

```powershell
docker-compose up -d --build
```

### 4) Validate demo pack against Docker

```powershell
.venv\Scripts\python scripts/run_demo_pack_live.py --base-url http://127.0.0.1:8000
```

Observed result:

```text
Demo pack validation passed for http://127.0.0.1:8000
```

## Validation Notes

- Async scenario `26_dpm_async_batch_analysis.json` validated:
  - `POST /rebalance/analyze/async` returns `202 Accepted`.
  - `GET /rebalance/operations/{operation_id}` returns terminal `SUCCEEDED`.
  - Result payload contains expected partial-batch warning and failed scenario diagnostics:
    - `warnings = ["PARTIAL_BATCH_FAILURE"]`
    - `failed_scenarios = {"invalid_options": "..."}`
- No contract or runtime mismatches observed between uvicorn and Docker paths.
- Supportability and artifact scenario `27_dpm_supportability_artifact_flow.json` validated:
  - `POST /rebalance/simulate` with idempotency + correlation headers succeeds.
  - `GET /rebalance/runs/{rebalance_run_id}` returns run payload and metadata.
  - `GET /rebalance/runs/by-correlation/{correlation_id}` returns mapped run.
  - `GET /rebalance/runs/idempotency/{idempotency_key}` returns mapped run id.
  - `GET /rebalance/runs/{rebalance_run_id}/artifact` returns deterministic artifact payload.
  - Repeated artifact retrieval returns identical `evidence.hashes.artifact_hash`.
- Async manual execute guard scenario `28_dpm_async_manual_execute_guard.json` validated:
  - `POST /rebalance/analyze/async` in default inline mode succeeds and completes operation.
  - `POST /rebalance/operations/{operation_id}/execute` returns `409` with
    `DPM_ASYNC_OPERATION_NOT_EXECUTABLE` when operation is already non-pending.
- Workflow gate contract scenario `29_dpm_workflow_gate_disabled_contract.json` validated:
  - `POST /rebalance/simulate` creates a pending-review candidate run.
  - `GET /rebalance/runs/{rebalance_run_id}/workflow` returns `404` with
    `DPM_WORKFLOW_DISABLED` under default config.
  - `GET /rebalance/runs/{rebalance_run_id}/workflow/history` returns `404` with
    `DPM_WORKFLOW_DISABLED` under default config.
- Additional workflow-enabled supportability checks validated:
  - Uvicorn (`DPM_WORKFLOW_ENABLED=true`, `http://127.0.0.1:8001`):
    - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow` returns `200`.
    - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow` returns `200`.
    - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow/history` returns `200`.
    - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow/history` returns `200`.
    - Workflow action and history are consistent between run-id and correlation-id endpoints.
    - Idempotency-key workflow retrieval without prior action returns:
      - `workflow_status=PENDING_REVIEW`
      - history `decisions=[]`
  - Container runtime (`dpm-rebalance-engine:latest` with `-e DPM_WORKFLOW_ENABLED=true`,
    published on `http://127.0.0.1:8002`):
    - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow` returns `200`.
    - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow` returns `200`.
    - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow/history` returns `200`.
    - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow/history` returns `200`.
    - Idempotency-key workflow retrieval without prior action returns:
      - `workflow_status=PENDING_REVIEW`
      - history `decisions=[]`
