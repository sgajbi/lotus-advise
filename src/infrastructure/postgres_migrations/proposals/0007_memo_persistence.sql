CREATE TABLE IF NOT EXISTS proposal_memos (
    memo_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    proposal_version_no INTEGER NOT NULL,
    proposal_version_id TEXT NULL,
    artifact_id TEXT NULL,
    memo_version TEXT NOT NULL,
    memo_status TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_input_hash TEXT NOT NULL,
    memo_hash TEXT NOT NULL,
    memo_json TEXT NOT NULL,
    projection_json TEXT NOT NULL,
    review_events_json TEXT NOT NULL,
    report_package_events_json TEXT NOT NULL,
    archive_refs_json TEXT NOT NULL,
    ai_refs_json TEXT NOT NULL,
    replay_metadata_json TEXT NOT NULL,
    UNIQUE (proposal_id, proposal_version_no)
);

CREATE TABLE IF NOT EXISTS proposal_memo_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    memo_id TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    proposal_version_no INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proposal_memo_events (
    event_id TEXT PRIMARY KEY,
    memo_id TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    proposal_version_no INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    reason_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_proposal_memos_proposal_version
    ON proposal_memos (proposal_id, proposal_version_no);

CREATE INDEX IF NOT EXISTS idx_proposal_memo_events_memo
    ON proposal_memo_events (memo_id, occurred_at, event_id);
