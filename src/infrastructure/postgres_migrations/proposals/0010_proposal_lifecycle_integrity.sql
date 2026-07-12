CREATE UNIQUE INDEX IF NOT EXISTS ux_proposal_versions_proposal_version_id
    ON proposal_versions (proposal_version_id);

ALTER TABLE proposal_records
    ADD CONSTRAINT ck_proposal_records_current_version_positive
    CHECK (current_version_no > 0) NOT VALID;

ALTER TABLE proposal_records
    ADD CONSTRAINT ck_proposal_records_current_state
    CHECK (
        current_state IN (
            'DRAFT',
            'RISK_REVIEW',
            'COMPLIANCE_REVIEW',
            'AWAITING_CLIENT_CONSENT',
            'EXECUTION_READY',
            'EXECUTED',
            'REJECTED',
            'CANCELLED',
            'EXPIRED'
        )
    ) NOT VALID;

ALTER TABLE proposal_versions
    ADD CONSTRAINT ck_proposal_versions_version_positive
    CHECK (version_no > 0) NOT VALID;

ALTER TABLE proposal_versions
    ADD CONSTRAINT ck_proposal_versions_status_at_creation
    CHECK (status_at_creation IN ('READY', 'PENDING_REVIEW', 'BLOCKED')) NOT VALID;

ALTER TABLE proposal_versions
    ADD CONSTRAINT fk_proposal_versions_proposal
    FOREIGN KEY (proposal_id)
    REFERENCES proposal_records (proposal_id)
    ON DELETE RESTRICT
    NOT VALID;

ALTER TABLE proposal_workflow_events
    ADD CONSTRAINT ck_proposal_workflow_events_event_type
    CHECK (
        event_type IN (
            'CREATED',
            'NEW_VERSION_CREATED',
            'SUBMITTED_FOR_RISK_REVIEW',
            'RISK_APPROVED',
            'SUBMITTED_FOR_COMPLIANCE_REVIEW',
            'COMPLIANCE_APPROVED',
            'CLIENT_CONSENT_RECORDED',
            'EXECUTION_REQUESTED',
            'EXECUTION_ACCEPTED',
            'EXECUTION_PARTIALLY_EXECUTED',
            'EXECUTION_REJECTED',
            'EXECUTION_CANCELLED',
            'EXECUTION_EXPIRED',
            'NARRATIVE_REVIEWED',
            'REPORT_REQUESTED',
            'EXECUTED',
            'REJECTED',
            'EXPIRED',
            'CANCELLED'
        )
    ) NOT VALID;

ALTER TABLE proposal_workflow_events
    ADD CONSTRAINT ck_proposal_workflow_events_states
    CHECK (
        (from_state IS NULL OR from_state IN (
            'DRAFT',
            'RISK_REVIEW',
            'COMPLIANCE_REVIEW',
            'AWAITING_CLIENT_CONSENT',
            'EXECUTION_READY',
            'EXECUTED',
            'REJECTED',
            'CANCELLED',
            'EXPIRED'
        ))
        AND to_state IN (
            'DRAFT',
            'RISK_REVIEW',
            'COMPLIANCE_REVIEW',
            'AWAITING_CLIENT_CONSENT',
            'EXECUTION_READY',
            'EXECUTED',
            'REJECTED',
            'CANCELLED',
            'EXPIRED'
        )
    ) NOT VALID;

ALTER TABLE proposal_workflow_events
    ADD CONSTRAINT ck_proposal_workflow_events_related_version_positive
    CHECK (related_version_no IS NULL OR related_version_no > 0) NOT VALID;

ALTER TABLE proposal_workflow_events
    ADD CONSTRAINT fk_proposal_workflow_events_proposal
    FOREIGN KEY (proposal_id)
    REFERENCES proposal_records (proposal_id)
    ON DELETE RESTRICT
    NOT VALID;

ALTER TABLE proposal_workflow_events
    ADD CONSTRAINT fk_proposal_workflow_events_related_version
    FOREIGN KEY (proposal_id, related_version_no)
    REFERENCES proposal_versions (proposal_id, version_no)
    ON DELETE RESTRICT
    NOT VALID;

ALTER TABLE proposal_approvals
    ADD CONSTRAINT ck_proposal_approvals_type
    CHECK (approval_type IN ('RISK', 'COMPLIANCE', 'CLIENT_CONSENT')) NOT VALID;

ALTER TABLE proposal_approvals
    ADD CONSTRAINT ck_proposal_approvals_related_version_positive
    CHECK (related_version_no IS NULL OR related_version_no > 0) NOT VALID;

ALTER TABLE proposal_approvals
    ADD CONSTRAINT fk_proposal_approvals_proposal
    FOREIGN KEY (proposal_id)
    REFERENCES proposal_records (proposal_id)
    ON DELETE RESTRICT
    NOT VALID;

ALTER TABLE proposal_approvals
    ADD CONSTRAINT fk_proposal_approvals_related_version
    FOREIGN KEY (proposal_id, related_version_no)
    REFERENCES proposal_versions (proposal_id, version_no)
    ON DELETE RESTRICT
    NOT VALID;

ALTER TABLE proposal_idempotency
    ADD CONSTRAINT ck_proposal_idempotency_version_positive
    CHECK (proposal_version_no > 0) NOT VALID;

ALTER TABLE proposal_idempotency
    ADD CONSTRAINT fk_proposal_idempotency_version
    FOREIGN KEY (proposal_id, proposal_version_no)
    REFERENCES proposal_versions (proposal_id, version_no)
    ON DELETE RESTRICT
    NOT VALID;

ALTER TABLE proposal_async_operations
    ADD CONSTRAINT fk_proposal_async_operations_proposal
    FOREIGN KEY (proposal_id)
    REFERENCES proposal_records (proposal_id)
    ON DELETE SET NULL
    NOT VALID;

ALTER TABLE proposal_records VALIDATE CONSTRAINT ck_proposal_records_current_version_positive;
ALTER TABLE proposal_records VALIDATE CONSTRAINT ck_proposal_records_current_state;
ALTER TABLE proposal_versions VALIDATE CONSTRAINT ck_proposal_versions_version_positive;
ALTER TABLE proposal_versions VALIDATE CONSTRAINT ck_proposal_versions_status_at_creation;
ALTER TABLE proposal_versions VALIDATE CONSTRAINT fk_proposal_versions_proposal;
ALTER TABLE proposal_workflow_events VALIDATE CONSTRAINT ck_proposal_workflow_events_event_type;
ALTER TABLE proposal_workflow_events VALIDATE CONSTRAINT ck_proposal_workflow_events_states;
ALTER TABLE proposal_workflow_events VALIDATE CONSTRAINT ck_proposal_workflow_events_related_version_positive;
ALTER TABLE proposal_workflow_events VALIDATE CONSTRAINT fk_proposal_workflow_events_proposal;
ALTER TABLE proposal_workflow_events VALIDATE CONSTRAINT fk_proposal_workflow_events_related_version;
ALTER TABLE proposal_approvals VALIDATE CONSTRAINT ck_proposal_approvals_type;
ALTER TABLE proposal_approvals VALIDATE CONSTRAINT ck_proposal_approvals_related_version_positive;
ALTER TABLE proposal_approvals VALIDATE CONSTRAINT fk_proposal_approvals_proposal;
ALTER TABLE proposal_approvals VALIDATE CONSTRAINT fk_proposal_approvals_related_version;
ALTER TABLE proposal_idempotency VALIDATE CONSTRAINT ck_proposal_idempotency_version_positive;
ALTER TABLE proposal_idempotency VALIDATE CONSTRAINT fk_proposal_idempotency_version;
ALTER TABLE proposal_async_operations VALIDATE CONSTRAINT fk_proposal_async_operations_proposal;
