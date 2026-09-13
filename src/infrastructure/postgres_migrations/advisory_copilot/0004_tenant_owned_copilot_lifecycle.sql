ALTER TABLE advisory_copilot_evidence_packets
    ADD COLUMN IF NOT EXISTS tenant_id TEXT;

ALTER TABLE advisory_copilot_run_idempotency
    ADD COLUMN IF NOT EXISTS tenant_id TEXT;

ALTER TABLE advisory_copilot_reviews
    ADD COLUMN IF NOT EXISTS tenant_id TEXT;

-- `tenant_id` on historical runs was populated before an admitted caller authority
-- existed.  Do not infer ownership: only new rows receive an admitted tenant.
ALTER TABLE advisory_copilot_runs
    ADD COLUMN IF NOT EXISTS admitted_tenant_id TEXT;

-- Existing rows lack an admitted authority and must remain inaccessible rather than assigned.
ALTER TABLE advisory_copilot_run_idempotency
    DROP CONSTRAINT IF EXISTS advisory_copilot_run_idempotency_pkey;

ALTER TABLE advisory_copilot_evidence_packets
    ADD CONSTRAINT advisory_copilot_evidence_packets_tenant_required
    CHECK (tenant_id IS NOT NULL) NOT VALID;

ALTER TABLE advisory_copilot_run_idempotency
    ADD CONSTRAINT advisory_copilot_run_idempotency_tenant_required
    CHECK (tenant_id IS NOT NULL) NOT VALID;

ALTER TABLE advisory_copilot_reviews
    ADD CONSTRAINT advisory_copilot_reviews_tenant_required
    CHECK (tenant_id IS NOT NULL) NOT VALID;

ALTER TABLE advisory_copilot_runs
    ADD CONSTRAINT advisory_copilot_runs_admitted_tenant_required
    CHECK (admitted_tenant_id IS NOT NULL) NOT VALID;

CREATE UNIQUE INDEX IF NOT EXISTS idx_advisory_copilot_packets_tenant_packet
    ON advisory_copilot_evidence_packets (tenant_id, evidence_packet_id);

CREATE INDEX IF NOT EXISTS idx_advisory_copilot_runs_tenant_run
    ON advisory_copilot_runs (admitted_tenant_id, run_id);

DROP INDEX IF EXISTS idx_advisory_copilot_runs_request_hash;

CREATE UNIQUE INDEX IF NOT EXISTS idx_advisory_copilot_runs_tenant_request_hash
    ON advisory_copilot_runs (admitted_tenant_id, request_hash)
    WHERE admitted_tenant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_advisory_copilot_reviews_tenant_run
    ON advisory_copilot_reviews (tenant_id, run_id, occurred_at ASC, review_id ASC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_advisory_copilot_idempotency_tenant_key
    ON advisory_copilot_run_idempotency (tenant_id, idempotency_key);
