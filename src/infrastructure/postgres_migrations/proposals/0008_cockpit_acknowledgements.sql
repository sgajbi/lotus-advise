CREATE TABLE IF NOT EXISTS advisor_cockpit_acknowledgements (
    acknowledgement_id TEXT PRIMARY KEY,
    action_item_id TEXT NOT NULL UNIQUE,
    action_item_version INTEGER NOT NULL,
    acknowledged_by TEXT NOT NULL,
    acknowledged_at TEXT NOT NULL,
    acknowledgement_note TEXT,
    correlation_id TEXT,
    reason_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS advisor_cockpit_acknowledgement_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    acknowledgement_id TEXT NOT NULL,
    action_item_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_advisor_cockpit_acknowledgements_action
    ON advisor_cockpit_acknowledgements (action_item_id);
