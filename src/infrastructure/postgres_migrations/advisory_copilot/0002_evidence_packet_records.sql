CREATE TABLE IF NOT EXISTS advisory_copilot_evidence_packets (
    evidence_packet_id TEXT PRIMARY KEY,
    evidence_packet_hash TEXT NOT NULL,
    action_family TEXT NOT NULL,
    audience TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    proposal_id TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    packet_json TEXT NOT NULL,
    reason_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_advisory_copilot_packets_proposal_created
    ON advisory_copilot_evidence_packets (proposal_id, created_at DESC, evidence_packet_id DESC);

CREATE INDEX IF NOT EXISTS idx_advisory_copilot_packets_portfolio_created
    ON advisory_copilot_evidence_packets (portfolio_id, created_at DESC, evidence_packet_id DESC);
