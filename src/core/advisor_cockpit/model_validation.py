from __future__ import annotations

COCKPIT_IDENTIFIER_MAX_LENGTH = 160
COCKPIT_TEXT_MAX_LENGTH = 1000
COCKPIT_SUMMARY_MAX_LENGTH = 512
COCKPIT_LIST_MAX_ITEMS = 64
COCKPIT_PREPARATION_SECTIONS_MAX_ITEMS = 32
COCKPIT_SUPPORTABILITY_KEYS_MAX_ITEMS = 64

_COCKPIT_SENSITIVE_TERMS = (
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "api key",
    "apikey",
    "raw prompt",
    "raw payload",
    "provider response",
)
_COCKPIT_OWNER_ROLE_LABELS = {
    "ADVISOR": "Advisor",
    "DESK_HEAD": "Desk head",
    "COMPLIANCE_REVIEWER": "Compliance reviewer",
    "INVESTMENT_DESK": "Investment desk",
    "PORTFOLIO_MANAGER": "Portfolio manager",
    "OPERATIONS": "Operations",
    "CRM_OWNER": "Client-relationship owner",
    "REPORTING_OWNER": "Reporting owner",
    "ARCHIVE_OWNER": "Archive owner",
    "EXECUTION_OWNER": "Execution owner",
    "SYSTEM": "System",
}


def cockpit_owner_role_label(role: str) -> str:
    return _COCKPIT_OWNER_ROLE_LABELS.get(role, role.replace("_", " ").title())


def normalize_required_identifier(value: str, *, field_name: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > COCKPIT_IDENTIFIER_MAX_LENGTH:
        raise ValueError(f"{field_name} is too long")
    if contains_sensitive_term(normalized):
        raise ValueError(f"{field_name} cannot contain sensitive technical detail")
    return normalized


def normalize_optional_identifier(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    return normalize_required_identifier(normalized, field_name=field_name)


def normalize_business_text(value: str, *, field_name: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > COCKPIT_TEXT_MAX_LENGTH:
        raise ValueError(f"{field_name} is too long")
    if contains_sensitive_term(normalized):
        raise ValueError(f"{field_name} cannot contain sensitive technical detail")
    return normalized


def normalize_optional_business_text(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    return normalize_business_text(normalized, field_name=field_name)


def normalize_identifier_list(value: list[str], *, field_name: str) -> list[str]:
    return [normalize_required_identifier(str(item), field_name=field_name) for item in value]


def contains_sensitive_term(value: str) -> bool:
    lowered = value.lower().replace("-", " ")
    return any(term in lowered for term in _COCKPIT_SENSITIVE_TERMS)
