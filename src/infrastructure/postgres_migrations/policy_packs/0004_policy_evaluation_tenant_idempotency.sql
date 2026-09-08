-- Partition caller-supplied policy-evaluation idempotency keys by admitted tenant.
ALTER TABLE policy_evaluation_idempotency
    ADD COLUMN IF NOT EXISTS tenant_id TEXT;

UPDATE policy_evaluation_idempotency AS idempotency
SET tenant_id = record.tenant_id
FROM policy_evaluation_records AS record
WHERE record.evaluation_id = idempotency.evaluation_id
  AND idempotency.tenant_id IS NULL
  AND record.tenant_id IS NOT NULL;

ALTER TABLE policy_evaluation_idempotency
    DROP CONSTRAINT IF EXISTS policy_evaluation_idempotency_pkey;

CREATE UNIQUE INDEX IF NOT EXISTS uq_policy_evaluation_idempotency_tenant_key
    ON policy_evaluation_idempotency (tenant_id, idempotency_key) NULLS NOT DISTINCT;
