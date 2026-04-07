CREATE UNIQUE INDEX IF NOT EXISTS idx_proposal_async_operations_idempotency_key
    ON proposal_async_operations (idempotency_key)
    WHERE idempotency_key IS NOT NULL;
