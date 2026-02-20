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
  - Async operation listing validation:
    - `GET /rebalance/operations?status=SUCCEEDED&operation_type=ANALYZE_SCENARIOS&limit=...`
      returns filtered operation rows.
    - Cursor pagination check:
      - `GET /rebalance/operations?limit=1` returns `next_cursor`.
      - `GET /rebalance/operations?limit=1&cursor={next_cursor}` returns next row.
  - Additional manual listing checks:
    - Uvicorn (`DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY`, `http://127.0.0.1:8017`):
      - `GET /rebalance/operations?operation_type=ANALYZE_SCENARIOS&status=PENDING&limit=10`
        returns expected pending operations.
      - cursor pagination over operations returns deterministic next row.
    - Container (`DPM_ASYNC_EXECUTION_MODE=ACCEPT_ONLY`, `http://127.0.0.1:8018`):
      - filtered listing and cursor pagination produce expected operation rows.
- Supportability summary API validation:
  - Uvicorn runtime (`http://127.0.0.1:8019`):
    - `POST /rebalance/simulate` returns `status=READY`.
    - `GET /rebalance/supportability/summary` returns `200` with:
      - `store_backend=IN_MEMORY`
      - `run_count=1`
      - `operation_count=0`
      - `run_status_counts={"READY":1}`
      - `workflow_decision_count=0`
      - `lineage_edge_count=2`
  - Docker runtime (`http://127.0.0.1:8000`):
    - `POST /rebalance/simulate` returns `status=READY`.
    - `GET /rebalance/supportability/summary` returns `200` with:
      - `store_backend=IN_MEMORY`
      - `run_count=1`
      - `operation_count=0`
      - `run_status_counts={"READY":1}`
      - `workflow_decision_count=0`
      - `lineage_edge_count=2`
  - Uvicorn runtime (`DPM_WORKFLOW_ENABLED=true`, `http://127.0.0.1:8035`):
    - `POST /rebalance/simulate` with pending-review candidate payload and one workflow `APPROVE` action.
    - `GET /rebalance/supportability/summary` returns:
      - `workflow_action_counts={"APPROVE":1}`
      - `workflow_reason_code_counts={"REVIEW_APPROVED":1}`
  - Container runtime (`DPM_WORKFLOW_ENABLED=true`, `http://127.0.0.1:8036`):
    - `POST /rebalance/simulate` with pending-review candidate payload and one workflow `APPROVE` action.
    - `GET /rebalance/supportability/summary` returns:
      - `workflow_action_counts={"APPROVE":1}`
      - `workflow_reason_code_counts={"REVIEW_APPROVED":1}`
- Run support bundle API validation:
  - Uvicorn runtime (`http://127.0.0.1:8022`):
    - `POST /rebalance/simulate` returns `status=READY`.
    - `GET /rebalance/runs/{rebalance_run_id}/support-bundle` returns `200` with:
      - `run.rebalance_run_id` matching created run id
      - `artifact` populated
      - `lineage.edges` count = `2`
      - `workflow_history.decisions` count = `0`
    - Correlation/idempotency variants:
      - `GET /rebalance/runs/by-correlation/{correlation_id}/support-bundle` returns `200`
        with run id matching simulate response.
      - `GET /rebalance/runs/idempotency/{idempotency_key}/support-bundle` returns `200`
        with run id matching simulate response.
      - `GET /rebalance/runs/by-operation/{operation_id}/support-bundle` returns `200`
        with run id matching simulate response after async operation creation.
  - Docker runtime (`http://127.0.0.1:8000`):
    - `POST /rebalance/simulate` returns `status=READY`.
    - `GET /rebalance/runs/{rebalance_run_id}/support-bundle` returns `200` with:
      - `run.rebalance_run_id` matching created run id
      - `artifact` populated
      - `lineage.edges` count = `2`
      - `workflow_history.decisions` count = `0`
    - Correlation/idempotency variants:
      - `GET /rebalance/runs/by-correlation/{correlation_id}/support-bundle` returns `200`
        with run id matching simulate response.
      - `GET /rebalance/runs/idempotency/{idempotency_key}/support-bundle` returns `200`
        with run id matching simulate response.
      - `GET /rebalance/runs/by-operation/{operation_id}/support-bundle` returns `200`
        with run id matching simulate response after async operation creation.
- SQLite supportability backend validation:
  - Uvicorn run (`DPM_SUPPORTABILITY_STORE_BACKEND=SQLITE`) on `http://127.0.0.1:8001`:
    - `POST /rebalance/simulate` succeeded (`200`).
    - `GET /rebalance/runs/{rebalance_run_id}` succeeded (`200`).
    - `GET /rebalance/runs/by-correlation/{correlation_id}` succeeded (`200`).
    - `GET /rebalance/runs/idempotency/{idempotency_key}` succeeded (`200`).
- Lineage API validation:
  - Uvicorn run (`DPM_LINEAGE_APIS_ENABLED=true`) on `http://127.0.0.1:8001`:
    - `GET /rebalance/lineage/{correlation_id}` returns `200` with `CORRELATION_TO_RUN`.
    - `GET /rebalance/lineage/{idempotency_key}` returns `200` with `IDEMPOTENCY_TO_RUN`.
    - `GET /rebalance/lineage/{operation_id}` returns `200` with `OPERATION_TO_CORRELATION`.
- Idempotency history API validation:
  - Uvicorn run (`DPM_IDEMPOTENCY_REPLAY_ENABLED=false`, `DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true`)
    on `http://127.0.0.1:8011`:
    - Two `POST /rebalance/simulate` calls with same idempotency key and different payload hash
      both return `200`.
    - `GET /rebalance/idempotency/{idempotency_key}/history` returns `200` with two entries
      preserving run ids, correlation ids, and request hashes.
  - Container run (`dpm-rebalance-engine:latest`, `DPM_IDEMPOTENCY_REPLAY_ENABLED=false`,
    `DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true`, `DPM_SUPPORTABILITY_STORE_BACKEND=SQLITE`)
    on `http://127.0.0.1:8012`:
    - Two `POST /rebalance/simulate` calls with same idempotency key and different payload hash
      both return `200`.
    - `GET /rebalance/idempotency/{idempotency_key}/history` returns `200` with two entries.
  - Container run (`DPM_LINEAGE_APIS_ENABLED=true`, `DPM_SUPPORTABILITY_STORE_BACKEND=SQLITE`)
    on `http://127.0.0.1:8002`:
    - `GET /rebalance/lineage/{correlation_id}` returns `200` with `CORRELATION_TO_RUN`.
    - `GET /rebalance/lineage/{idempotency_key}` returns `200` with `IDEMPOTENCY_TO_RUN`.
    - `GET /rebalance/lineage/{operation_id}` returns `200` with `OPERATION_TO_CORRELATION`.
  - Container run (`dpm-rebalance-engine:latest` with `DPM_SUPPORTABILITY_STORE_BACKEND=SQLITE`)
    on `http://127.0.0.1:8002`:
    - `POST /rebalance/simulate` succeeded (`200`).
    - `GET /rebalance/runs/{rebalance_run_id}` succeeded (`200`).
    - `GET /rebalance/runs/by-correlation/{correlation_id}` succeeded (`200`).
    - `GET /rebalance/runs/idempotency/{idempotency_key}` succeeded (`200`).
- Supportability and artifact scenario `27_dpm_supportability_artifact_flow.json` validated:
  - `POST /rebalance/simulate` with idempotency + correlation headers succeeds.
  - `GET /rebalance/runs/{rebalance_run_id}` returns run payload and metadata.
  - `GET /rebalance/runs/by-correlation/{correlation_id}` returns mapped run.
  - `GET /rebalance/runs/idempotency/{idempotency_key}` returns mapped run id.
  - `GET /rebalance/runs?status=READY&portfolio_id={portfolio_id}&limit=...` returns filtered rows.
  - Cursor pagination check:
    - `GET /rebalance/runs?limit=1` returns `next_cursor`.
    - `GET /rebalance/runs?limit=1&cursor={next_cursor}` returns next row.
  - `GET /rebalance/runs/{rebalance_run_id}/artifact` returns deterministic artifact payload.
  - Repeated artifact retrieval returns identical `evidence.hashes.artifact_hash`.
- Supportability run-list and retention validation:
  - Uvicorn (`DPM_SUPPORTABILITY_STORE_BACKEND=SQLITE`,
    `DPM_SUPPORTABILITY_RETENTION_DAYS=1`, `http://127.0.0.1:8015`):
    - `POST /rebalance/simulate` succeeds and appears in `GET /rebalance/runs`.
    - After setting persisted run timestamp older than retention window in SQLite,
      `GET /rebalance/runs` returns empty list (expired run purged).
  - Container (`DPM_SUPPORTABILITY_STORE_BACKEND=SQLITE`,
    `DPM_SUPPORTABILITY_RETENTION_DAYS=1`, `http://127.0.0.1:8016`):
    - `POST /rebalance/simulate` succeeds and appears in `GET /rebalance/runs`.
    - After setting persisted run timestamp older than retention window in SQLite,
      `GET /rebalance/runs` returns empty list (expired run purged).
- Request-hash run-list filtering validation:
  - Uvicorn runtime (`http://127.0.0.1:8025`):
    - `POST /rebalance/simulate` succeeds.
    - `GET /rebalance/runs/{rebalance_run_id}` returns persisted `request_hash`.
    - `GET /rebalance/runs?request_hash={request_hash}&limit=20` returns one matching run.
    - `GET /rebalance/runs/by-request-hash/{url_encoded_request_hash}` returns matching run.
  - Docker runtime (`http://127.0.0.1:8000`):
    - `POST /rebalance/simulate` succeeds.
    - `GET /rebalance/runs/{rebalance_run_id}` returns persisted `request_hash`.
    - `GET /rebalance/runs?request_hash={request_hash}&limit=20` returns one matching run.
    - `GET /rebalance/runs/by-request-hash/{url_encoded_request_hash}` returns matching run.
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
  - Uvicorn runtime (`DPM_WORKFLOW_ENABLED=true`, `http://127.0.0.1:8032`):
    - `POST /rebalance/simulate` returns `200` for workflow-review candidate payload.
    - `POST /rebalance/runs/{rebalance_run_id}/workflow/actions` with `APPROVE` returns `200`.
    - `GET /rebalance/workflow/decisions?actor_id=reviewer_manual_uvicorn&action=APPROVE&limit=10`
      returns `200` with one matching decision.
    - `GET /rebalance/workflow/decisions/by-correlation/corr-manual-wf-uvicorn`
      returns `200` with decision history for the resolved run.
  - Uvicorn runtime (`DPM_WORKFLOW_ENABLED=true`, `http://127.0.0.1:8033`):
    - `POST /rebalance/simulate` + one workflow `APPROVE` action succeeded.
    - `GET /rebalance/workflow/decisions/by-correlation/corr-manual-wf-corr-uvicorn`
      returns `200` with `run_id=rr_b5a85230` and one decision.
  - Uvicorn (`DPM_WORKFLOW_ENABLED=true`, `http://127.0.0.1:8001`):
    - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow` returns `200`.
    - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow` returns `200`.
    - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow/history` returns `200`.
    - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow/history` returns `200`.
    - `POST /rebalance/runs/by-correlation/{correlation_id}/workflow/actions` returns `200`.
    - `POST /rebalance/runs/idempotency/{idempotency_key}/workflow/actions` returns `200`.
    - Sequential action check:
      - correlation-based `REQUEST_CHANGES` keeps workflow in `PENDING_REVIEW`
      - idempotency-based `APPROVE` transitions workflow to `APPROVED`
    - Workflow action and history are consistent between run-id and correlation-id endpoints.
    - Idempotency-key workflow retrieval without prior action returns:
      - `workflow_status=PENDING_REVIEW`
      - history `decisions=[]`
    - `GET /rebalance/workflow/decisions?limit=20` returns workflow decisions across runs.
    - `GET /rebalance/workflow/decisions?actor_id=...&action=...&limit=...` returns filtered rows.
  - Container runtime (`dpm-rebalance-engine:latest` with `-e DPM_WORKFLOW_ENABLED=true`,
    published on `http://127.0.0.1:8002`):
    - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow` returns `200`.
    - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow` returns `200`.
    - `GET /rebalance/runs/by-correlation/{correlation_id}/workflow/history` returns `200`.
    - `GET /rebalance/runs/idempotency/{idempotency_key}/workflow/history` returns `200`.
    - `POST /rebalance/runs/by-correlation/{correlation_id}/workflow/actions` returns `200`.
    - `POST /rebalance/runs/idempotency/{idempotency_key}/workflow/actions` returns `200`.
    - Sequential action check:
      - correlation-based `REQUEST_CHANGES` keeps workflow in `PENDING_REVIEW`
      - idempotency-based `APPROVE` transitions workflow to `APPROVED`
    - Idempotency-key workflow retrieval without prior action returns:
      - `workflow_status=PENDING_REVIEW`
      - history `decisions=[]`
  - Container runtime (`dpm-rebalance-engine:latest` with `-e DPM_WORKFLOW_ENABLED=true`,
    published on `http://127.0.0.1:8031`):
    - `POST /rebalance/simulate` returns `200`.
    - `POST /rebalance/runs/{rebalance_run_id}/workflow/actions` with `APPROVE` returns `200`.
    - `GET /rebalance/workflow/decisions?actor_id=reviewer_manual_docker&action=APPROVE&limit=10`
      returns `200` with one matching decision.
    - `GET /rebalance/workflow/decisions/by-correlation/corr-manual-wf-docker`
      returns `200` with decision history for the resolved run.
  - Container runtime (`dpm-rebalance-engine:latest` with `-e DPM_WORKFLOW_ENABLED=true`,
    published on `http://127.0.0.1:8034`):
    - `POST /rebalance/simulate` + one workflow `APPROVE` action succeeded.
    - `GET /rebalance/workflow/decisions/by-correlation/corr-manual-wf-corr-docker`
      returns `200` with `run_id=rr_7d3afe35` and one decision.
- Policy-pack scaffold validation (RFC-0022 slice 1):
  - Uvicorn runtime (`DPM_POLICY_PACKS_ENABLED=true`, `DPM_DEFAULT_POLICY_PACK_ID=dpm_default_pack`,
    `http://127.0.0.1:8037`):
    - `POST /rebalance/simulate` with `X-Policy-Pack-Id=dpm_request_pack` returns `200`
      and unchanged simulation behavior (`status=READY` observed).
  - Container runtime (`DPM_POLICY_PACKS_ENABLED=true`, `DPM_DEFAULT_POLICY_PACK_ID=dpm_default_pack`,
    `http://127.0.0.1:8038`):
    - `POST /rebalance/simulate` with `X-Policy-Pack-Id=dpm_request_pack` returns `200`
      and unchanged simulation behavior (`status=READY` observed).
    - `GET /rebalance/workflow/decisions?limit=20` returns workflow decisions across runs.
    - `GET /rebalance/workflow/decisions?actor_id=...&action=...&limit=...` returns filtered rows.
