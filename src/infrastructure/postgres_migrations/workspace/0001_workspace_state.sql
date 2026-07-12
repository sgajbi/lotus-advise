CREATE TABLE IF NOT EXISTS advisory_workspace_sessions (
    workspace_id TEXT PRIMARY KEY,
    workspace_name TEXT NOT NULL,
    input_mode TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    retention_status TEXT NOT NULL DEFAULT 'ACTIVE',
    resolved_context_hash TEXT,
    latest_evaluation_request_hash TEXT,
    lifecycle_proposal_id TEXT,
    lifecycle_proposal_version_no INTEGER,
    lifecycle_link_json TEXT NOT NULL,
    session_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS advisory_workspace_saved_versions (
    workspace_id TEXT NOT NULL REFERENCES advisory_workspace_sessions(workspace_id),
    workspace_version_id TEXT NOT NULL,
    version_no INTEGER NOT NULL,
    saved_by TEXT NOT NULL,
    saved_at TEXT NOT NULL,
    draft_state_hash TEXT NOT NULL,
    evaluation_request_hash TEXT,
    replay_evidence_json TEXT NOT NULL,
    saved_version_json TEXT NOT NULL,
    PRIMARY KEY (workspace_id, workspace_version_id),
    UNIQUE (workspace_id, version_no)
);

CREATE TABLE IF NOT EXISTS advisory_workspace_events (
    workspace_id TEXT NOT NULL REFERENCES advisory_workspace_sessions(workspace_id),
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    idempotency_key TEXT,
    request_hash TEXT,
    event_json TEXT NOT NULL,
    PRIMARY KEY (workspace_id, event_id)
);

CREATE TABLE IF NOT EXISTS advisory_workspace_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES advisory_workspace_sessions(workspace_id),
    operation_name TEXT NOT NULL,
    response_ref_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_advisory_workspace_sessions_lifecycle_link
    ON advisory_workspace_sessions (lifecycle_proposal_id, lifecycle_proposal_version_no)
    WHERE lifecycle_proposal_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_advisory_workspace_saved_versions_lookup
    ON advisory_workspace_saved_versions (workspace_id, saved_at DESC, workspace_version_id);

CREATE INDEX IF NOT EXISTS idx_advisory_workspace_events_lookup
    ON advisory_workspace_events (workspace_id, occurred_at, event_id);
