CREATE TABLE IF NOT EXISTS advisory_copilot_runs (
    run_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    action_family TEXT NOT NULL,
    audience TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    proposal_id TEXT,
    evidence_packet_id TEXT NOT NULL,
    evidence_packet_hash TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    output_hash TEXT NOT NULL,
    review_posture TEXT NOT NULL,
    client_ready_publication TEXT NOT NULL,
    retention_class TEXT NOT NULL,
    legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
    retention_expires_at TEXT,
    created_by TEXT NOT NULL,
    caller_app TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    idempotency_key TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    lotus_ai_workflow_run_id TEXT,
    lotus_ai_model_version TEXT,
    workflow_pack_id TEXT NOT NULL,
    workflow_pack_version TEXT NOT NULL,
    prompt_template_version TEXT NOT NULL,
    output_schema_version TEXT NOT NULL,
    evaluation_pack_ref TEXT NOT NULL,
    evidence_packet_json TEXT NOT NULL,
    request_summary_json TEXT NOT NULL,
    output_sections_json TEXT NOT NULL,
    review_guidance_json TEXT NOT NULL,
    guardrail_results_json TEXT NOT NULL,
    lineage_json TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_advisory_copilot_runs_request_hash
    ON advisory_copilot_runs (request_hash);

CREATE INDEX IF NOT EXISTS idx_advisory_copilot_runs_proposal_created
    ON advisory_copilot_runs (proposal_id, created_at DESC, run_id DESC);

CREATE INDEX IF NOT EXISTS idx_advisory_copilot_runs_portfolio_created
    ON advisory_copilot_runs (portfolio_id, created_at DESC, run_id DESC);

CREATE INDEX IF NOT EXISTS idx_advisory_copilot_runs_review_posture
    ON advisory_copilot_runs (review_posture, created_at DESC);

CREATE TABLE IF NOT EXISTS advisory_copilot_run_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES advisory_copilot_runs(run_id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS advisory_copilot_reviews (
    review_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES advisory_copilot_runs(run_id),
    schema_version TEXT NOT NULL,
    action TEXT NOT NULL,
    previous_posture TEXT NOT NULL,
    new_posture TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    reason_json TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    idempotency_key TEXT,
    correlation_id TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_advisory_copilot_reviews_idempotency
    ON advisory_copilot_reviews (run_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_advisory_copilot_reviews_run_time
    ON advisory_copilot_reviews (run_id, occurred_at ASC, review_id ASC);
