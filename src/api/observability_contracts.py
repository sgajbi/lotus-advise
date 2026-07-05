ADVISORY_SUPPORTABILITY_METRIC_LABELS: tuple[str, ...] = (
    "state",
    "reason",
    "freshness_bucket",
)

POLICY_EVALUATION_OPERATION_METRIC_LABELS: tuple[str, ...] = (
    "operation",
    "status",
    "reason",
    "dependency",
)

POLICY_EVALUATION_OPERATION_FORBIDDEN_LABEL_FIELDS: tuple[str, ...] = (
    "evaluation_id",
    "proposal_id",
    "portfolio_id",
    "actor_id",
    "report_request_id",
    "trace_id",
    "correlation_id",
    "request_id",
    "raw_error",
    "request_path",
    "prompt",
    "source_payload",
    "policy_text",
)
