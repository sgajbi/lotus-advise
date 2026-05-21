CREATE INDEX IF NOT EXISTS idx_proposal_records_list_created
    ON proposal_records (created_at DESC, proposal_id DESC);

CREATE INDEX IF NOT EXISTS idx_proposal_records_list_portfolio_state_advisor
    ON proposal_records (
        portfolio_id,
        current_state,
        created_by,
        created_at DESC,
        proposal_id DESC
    );
