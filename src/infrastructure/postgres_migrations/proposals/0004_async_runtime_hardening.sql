ALTER TABLE proposal_async_operations
    ADD COLUMN IF NOT EXISTS payload_json TEXT NOT NULL DEFAULT '{}';

ALTER TABLE proposal_async_operations
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE proposal_async_operations
    ADD COLUMN IF NOT EXISTS max_attempts INTEGER NOT NULL DEFAULT 3;

ALTER TABLE proposal_async_operations
    ADD COLUMN IF NOT EXISTS lease_expires_at TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_proposal_async_operations_recovery
    ON proposal_async_operations (status, lease_expires_at, created_at);
