from __future__ import annotations

from src.api.enterprise_readiness import authorize_write_request, redact_sensitive


def test_authorize_write_request_rejects_blank_enterprise_headers(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")

    authorized, reason = authorize_write_request(
        "POST",
        "/advisory/proposals",
        {
            "X-Actor-Id": "   ",
            "X-Tenant-Id": "tenant-sg-001",
            "X-Role": "ADVISOR",
            "X-Correlation-Id": "corr-001",
            "X-Service-Identity": "lotus-workbench",
        },
    )
    service_authorized, service_reason = authorize_write_request(
        "POST",
        "/advisory/proposals",
        {
            "X-Actor-Id": "advisor-sg-001",
            "X-Tenant-Id": "tenant-sg-001",
            "X-Role": "ADVISOR",
            "X-Correlation-Id": "corr-001",
            "X-Service-Identity": "   ",
        },
    )

    assert authorized is False
    assert reason == "missing_headers:x-actor-id"
    assert service_authorized is False
    assert service_reason == "missing_service_identity"


def test_authorize_write_request_trims_headers_and_capabilities(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv(
        "ENTERPRISE_CAPABILITY_RULES_JSON",
        '{"POST /advisory/proposals": "advisory.proposals.write"}',
    )

    authorized, reason = authorize_write_request(
        "POST",
        "/advisory/proposals",
        {
            " X-Actor-Id ": " advisor-sg-001 ",
            "X-Tenant-Id": " tenant-sg-001 ",
            "X-Role": " ADVISOR ",
            "X-Correlation-Id": " corr-001 ",
            "X-Service-Identity": " lotus-workbench ",
            "X-Capabilities": " advisory.proposals.write ",
        },
    )

    assert authorized is True
    assert reason is None


def test_authorize_write_request_does_not_match_sibling_capability_paths(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv(
        "ENTERPRISE_CAPABILITY_RULES_JSON",
        '{"POST /advisory/proposals": "advisory.proposals.write"}',
    )
    headers = {
        "X-Actor-Id": "advisor-sg-001",
        "X-Tenant-Id": "tenant-sg-001",
        "X-Role": "ADVISOR",
        "X-Correlation-Id": "corr-001",
        "X-Service-Identity": "lotus-workbench",
    }

    child_authorized, child_reason = authorize_write_request(
        "POST",
        "/advisory/proposals/pp_001",
        {**headers, "X-Capabilities": "advisory.proposals.write"},
    )
    sibling_authorized, sibling_reason = authorize_write_request(
        "POST",
        "/advisory/proposals-extra",
        headers,
    )

    assert child_authorized is True
    assert child_reason is None
    assert sibling_authorized is True
    assert sibling_reason is None


def test_redact_sensitive_covers_common_audit_metadata_key_variants() -> None:
    metadata = {
        "apiToken": "token-value",
        "authorizationHeader": "Bearer token-value",
        "client-email": "client@example.invalid",
        "safe_business_key": "portfolio review requested",
        "nested": {
            "privateKey": "private-key-value",
            "accountNumber": "12345678",
            "normal": "kept",
        },
        "items": [
            {"session_cookie": "cookie-value"},
            {"reason": "advisor review"},
        ],
        1001: {"token": "nested-token"},
    }

    redacted = redact_sensitive(metadata)

    assert redacted["apiToken"] == "***REDACTED***"
    assert redacted["authorizationHeader"] == "***REDACTED***"
    assert redacted["client-email"] == "***REDACTED***"
    assert redacted["nested"]["privateKey"] == "***REDACTED***"
    assert redacted["nested"]["accountNumber"] == "***REDACTED***"
    assert redacted["items"][0]["session_cookie"] == "***REDACTED***"
    assert redacted[1001]["token"] == "***REDACTED***"
    assert redacted["safe_business_key"] == "portfolio review requested"
    assert redacted["nested"]["normal"] == "kept"
    assert redacted["items"][1]["reason"] == "advisor review"


def test_redact_sensitive_does_not_mutate_original_metadata() -> None:
    metadata = {"token": "token-value", "nested": {"client_email": "client@example.invalid"}}

    redacted = redact_sensitive(metadata)

    assert redacted == {
        "token": "***REDACTED***",
        "nested": {"client_email": "***REDACTED***"},
    }
    assert metadata == {
        "token": "token-value",
        "nested": {"client_email": "client@example.invalid"},
    }
