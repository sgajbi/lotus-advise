from typing import Literal

ProposalWorkflowState = Literal[
    "DRAFT",
    "RISK_REVIEW",
    "COMPLIANCE_REVIEW",
    "AWAITING_CLIENT_CONSENT",
    "EXECUTION_READY",
    "EXECUTED",
    "REJECTED",
    "CANCELLED",
    "EXPIRED",
]

ProposalWorkflowEventType = Literal[
    "CREATED",
    "NEW_VERSION_CREATED",
    "SUBMITTED_FOR_RISK_REVIEW",
    "RISK_APPROVED",
    "SUBMITTED_FOR_COMPLIANCE_REVIEW",
    "COMPLIANCE_APPROVED",
    "CLIENT_CONSENT_RECORDED",
    "EXECUTION_REQUESTED",
    "EXECUTION_ACCEPTED",
    "EXECUTION_PARTIALLY_EXECUTED",
    "EXECUTION_REJECTED",
    "EXECUTION_CANCELLED",
    "EXECUTION_EXPIRED",
    "NARRATIVE_REVIEWED",
    "REPORT_REQUESTED",
    "EXECUTED",
    "REJECTED",
    "EXPIRED",
    "CANCELLED",
]

ProposalApprovalType = Literal["RISK", "COMPLIANCE", "CLIENT_CONSENT"]
ProposalCreationStatus = Literal["READY", "PENDING_REVIEW", "BLOCKED"]
ProposalAsyncOperationType = Literal["CREATE_PROPOSAL", "CREATE_PROPOSAL_VERSION"]
ProposalAsyncOperationStatus = Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED"]
ProposalLifecycleOrigin = Literal["DIRECT_CREATE", "WORKSPACE_HANDOFF"]
ProposalReportType = Literal["PORTFOLIO_REVIEW", "CLIENT_PROPOSAL_SUMMARY"]
ProposalExecutionHandoffStatus = Literal[
    "NOT_REQUESTED",
    "REQUESTED",
    "ACCEPTED",
    "PARTIALLY_EXECUTED",
    "EXECUTED",
    "REJECTED",
    "CANCELLED",
    "EXPIRED",
]
ProposalExecutionUpdateStatus = Literal[
    "ACCEPTED",
    "PARTIALLY_EXECUTED",
    "REJECTED",
    "CANCELLED",
    "EXPIRED",
    "EXECUTED",
]
ProposalInputMode = Literal["stateless", "stateful"]
