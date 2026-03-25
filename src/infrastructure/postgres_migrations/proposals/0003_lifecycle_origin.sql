ALTER TABLE proposal_records
ADD COLUMN IF NOT EXISTS lifecycle_origin TEXT NOT NULL DEFAULT 'DIRECT_CREATE';

ALTER TABLE proposal_records
ADD COLUMN IF NOT EXISTS source_workspace_id TEXT NULL;
