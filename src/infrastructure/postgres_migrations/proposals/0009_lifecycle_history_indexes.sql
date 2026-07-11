CREATE INDEX IF NOT EXISTS idx_proposal_workflow_events_history
    ON proposal_workflow_events (proposal_id, occurred_at ASC, event_id ASC);

CREATE INDEX IF NOT EXISTS idx_proposal_approvals_history
    ON proposal_approvals (proposal_id, occurred_at ASC, approval_id ASC);
