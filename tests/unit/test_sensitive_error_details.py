from src.core.common.sensitive_error_details import contains_sensitive_error_detail


def test_sensitive_error_detail_redacts_identifier_values() -> None:
    assert contains_sensitive_error_detail("VALIDATION_INVALID trace_id=trace-should-not-leak")
    assert contains_sensitive_error_detail("VALIDATION_INVALID correlation-id=corr-should-not-leak")


def test_sensitive_error_detail_allows_stable_domain_codes() -> None:
    assert not contains_sensitive_error_detail(
        "CORRELATION_ID_CONFLICT: async version submission mismatch"
    )
    assert not contains_sensitive_error_detail("TRACE_ID_REQUIRED")
