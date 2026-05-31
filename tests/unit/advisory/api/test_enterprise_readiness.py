from __future__ import annotations

from src.api.enterprise_readiness import redact_sensitive


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
