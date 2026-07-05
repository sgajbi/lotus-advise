CREATE TABLE IF NOT EXISTS policy_evaluation_records (
    evaluation_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    proposal_version_id TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    policy_pack_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    evaluation_status TEXT NOT NULL,
    source_evidence_hash TEXT NOT NULL,
    policy_content_hash TEXT NOT NULL,
    evaluation_hash TEXT NOT NULL,
    record_json TEXT NOT NULL,
    UNIQUE (
        proposal_id,
        proposal_version_id,
        policy_pack_id,
        policy_version,
        source_evidence_hash
    )
);

CREATE TABLE IF NOT EXISTS policy_evaluation_audit_events (
    evaluation_id TEXT NOT NULL REFERENCES policy_evaluation_records(evaluation_id),
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    idempotency_key TEXT,
    request_hash TEXT NOT NULL,
    event_json TEXT NOT NULL,
    PRIMARY KEY (evaluation_id, event_id)
);

CREATE TABLE IF NOT EXISTS policy_evaluation_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    evaluation_id TEXT NOT NULL REFERENCES policy_evaluation_records(evaluation_id),
    event_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_policy_evaluation_records_review_queue
    ON policy_evaluation_records (evaluation_status, portfolio_id, generated_at);

CREATE INDEX IF NOT EXISTS idx_policy_evaluation_events_lookup
    ON policy_evaluation_audit_events (evaluation_id, occurred_at, event_id);

CREATE TABLE IF NOT EXISTS policy_pack_catalog_versions (
    policy_pack_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    activation_state TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    definition_json TEXT NOT NULL,
    PRIMARY KEY (policy_pack_id, policy_version)
);

CREATE TABLE IF NOT EXISTS policy_pack_catalog_audit_events (
    policy_pack_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    idempotency_key TEXT,
    request_hash TEXT NOT NULL,
    event_json TEXT NOT NULL,
    PRIMARY KEY (policy_pack_id, policy_version, event_id)
);

CREATE TABLE IF NOT EXISTS policy_pack_catalog_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    policy_pack_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    event_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_policy_pack_catalog_active_version
    ON policy_pack_catalog_versions (policy_pack_id, policy_version)
    WHERE activation_state = 'ACTIVE';

CREATE INDEX IF NOT EXISTS idx_policy_pack_catalog_events_lookup
    ON policy_pack_catalog_audit_events (policy_pack_id, policy_version, occurred_at, event_id);
