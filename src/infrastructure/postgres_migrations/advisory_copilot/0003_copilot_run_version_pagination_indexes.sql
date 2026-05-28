CREATE INDEX IF NOT EXISTS idx_advisory_copilot_runs_version_id_created
    ON advisory_copilot_runs (
        proposal_id,
        ((lineage_json::jsonb ->> 'proposal_version_id')),
        created_at DESC,
        run_id DESC
    );

CREATE INDEX IF NOT EXISTS idx_advisory_copilot_runs_version_no_created
    ON advisory_copilot_runs (
        proposal_id,
        ((lineage_json::jsonb ->> 'proposal_version_no')),
        created_at DESC,
        run_id DESC
    );
