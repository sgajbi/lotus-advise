from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, cast

from src.core.proposals.correlation import MAX_CORRELATION_ID_LENGTH

_SNAPSHOT_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_DEFAULT_ACTOR_ID = "lotus-advise"
_DEFAULT_TENANT_ID = "tenant-sg-001"


class LotusReportRequestMappingError(ValueError):
    """Raised when an Advise-to-Report request cannot be safely projected."""


def report_request_id(request: dict[str, Any]) -> str:
    return required_string(request, "report_request_id")


def build_report_headers(
    *,
    request: dict[str, Any],
    request_id: str,
    tenant_id: str | None,
) -> dict[str, str]:
    region = proposal_region(request)
    return {
        "Idempotency-Key": request_id,
        "X-Actor-Id": report_actor_id(request),
        "X-Caller-Application": "lotus-advise",
        "X-Tenant-Id": bounded_tenant_id(tenant_id),
        "X-Region": region,
        "X-Booking-Center-Code": region,
        "X-Role": "advisor",
    }


def build_portfolio_review_job_request(request: dict[str, Any]) -> dict[str, Any]:
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    portfolio_id = required_string(proposal, "portfolio_id")
    related_version_no = request.get("related_version_no")
    proposal_narrative_package = request.get("proposal_narrative_package")
    payload: dict[str, Any] = {
        "portfolio_scope": {"portfolio_ids": [portfolio_id]},
        "as_of_date": extract_report_as_of_date(request),
        "requested_output_formats": ["json"],
        "reporting_currency": extract_reporting_currency(request),
        "options": {
            "source_system": "lotus-advise",
            "source_proposal_id": proposal.get("proposal_id"),
            "source_report_type": request.get("report_type"),
            "requested_by": report_actor_id(request),
            "related_version_no": related_version_no,
            "include_execution_summary": request.get("include_execution_summary"),
            "include_reviewed_narrative": request.get("include_reviewed_narrative"),
        },
    }
    if isinstance(proposal_narrative_package, dict):
        payload["proposal_narrative_package"] = proposal_narrative_package
    return payload


def build_memo_report_package_job_request(request: dict[str, Any]) -> dict[str, Any]:
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    portfolio_id = required_string(proposal, "portfolio_id")
    payload = {
        "portfolio_scope": {"portfolio_ids": [portfolio_id]},
        "as_of_date": extract_report_as_of_date(request),
        "requested_output_formats": normalized_output_formats(
            request.get("requested_output_formats")
        ),
        "reporting_currency": extract_reporting_currency(request),
        "options": {
            "source_system": "lotus-advise",
            "source_proposal_id": proposal.get("proposal_id"),
            "source_report_type": "ADVISORY_PROPOSAL_MEMO",
            "requested_by": report_actor_id(request),
            "related_version_no": request.get("related_version_no"),
            "retention_policy_id": as_mapping(request.get("reason")).get("retention_policy_id"),
        },
        "proposal_memo_package": request.get("proposal_memo_package"),
    }
    return payload


def build_policy_sign_off_package_job_request(request: dict[str, Any]) -> dict[str, Any]:
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    portfolio_id = required_string(proposal, "portfolio_id")
    payload = {
        "portfolio_scope": {"portfolio_ids": [portfolio_id]},
        "as_of_date": extract_report_as_of_date(request),
        "requested_output_formats": normalized_output_formats(
            request.get("requested_output_formats")
        ),
        "reporting_currency": extract_reporting_currency(request),
        "options": {
            "source_system": "lotus-advise",
            "source_proposal_id": proposal.get("proposal_id"),
            "source_report_type": "ADVISORY_POLICY_SIGN_OFF_PACKAGE",
            "requested_by": report_actor_id(request),
            "related_policy_evaluation_id": request.get("related_policy_evaluation_id"),
            "retention_policy_id": as_mapping(request.get("reason")).get("retention_policy_id"),
        },
        "policy_sign_off_package": request.get("policy_sign_off_package"),
    }
    return payload


def normalized_output_formats(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["pdf"]
    normalized = [
        str(item).strip().lower() for item in value if str(item).strip().lower() in {"pdf", "json"}
    ]
    return normalized or ["pdf"]


def extract_report_as_of_date(request: dict[str, Any]) -> str:
    proposal_version = cast(dict[str, Any], request.get("proposal_version") or {})
    proposal_result = cast(dict[str, Any], proposal_version.get("proposal_result") or {})
    direct_date = find_first_key_value(
        proposal_result,
        keys={"as_of_date", "report_end_date", "valuation_date"},
    )
    if direct_date is not None:
        return direct_date
    lineage = proposal_result.get("lineage")
    if isinstance(lineage, dict):
        for value in lineage.values():
            if isinstance(value, str):
                match = _SNAPSHOT_DATE_PATTERN.search(value)
                if match:
                    return match.group(0)
    return datetime.now(UTC).date().isoformat()


def extract_reporting_currency(request: dict[str, Any]) -> str | None:
    proposal_version = cast(dict[str, Any], request.get("proposal_version") or {})
    proposal_result = cast(dict[str, Any], proposal_version.get("proposal_result") or {})
    before = proposal_result.get("before")
    if isinstance(before, dict):
        total_value = before.get("total_value")
        if isinstance(total_value, dict):
            currency = optional_string(total_value.get("currency"))
            if currency:
                return currency
    return "USD"


def find_first_key_value(payload: Any, *, keys: set[str]) -> str | None:
    if isinstance(payload, dict):
        return find_first_key_value_in_mapping(payload, keys=keys)
    if isinstance(payload, list):
        return find_first_key_value_in_sequence(payload, keys=keys)
    return None


def find_first_key_value_in_mapping(
    payload: dict[str, Any],
    *,
    keys: set[str],
) -> str | None:
    for key, value in payload.items():
        if key in keys:
            normalized = normalized_snapshot_date(value)
            if normalized:
                return normalized
        nested = find_first_key_value(value, keys=keys)
        if nested:
            return nested
    return None


def find_first_key_value_in_sequence(
    payload: list[Any],
    *,
    keys: set[str],
) -> str | None:
    for value in payload:
        nested = find_first_key_value(value, keys=keys)
        if nested:
            return nested
    return None


def normalized_snapshot_date(value: Any) -> str | None:
    normalized = optional_string(value)
    if normalized and _SNAPSHOT_DATE_PATTERN.fullmatch(normalized):
        return normalized
    return None


def proposal_region(request: dict[str, Any]) -> str:
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    return optional_string(proposal.get("jurisdiction")) or "SG"


def report_actor_id(request: dict[str, Any]) -> str:
    return bounded_identity(request.get("requested_by"), default=_DEFAULT_ACTOR_ID)


def bounded_tenant_id(value: Any) -> str:
    return bounded_identity(value, default=_DEFAULT_TENANT_ID)


def report_status_path(status_url: Any) -> str | None:
    normalized = optional_string(status_url)
    if normalized is None or any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        return None
    if "?" in normalized or "#" in normalized:
        return None
    if not normalized.startswith("/reports/jobs/"):
        return None
    return normalized


def normalize_report_job_status(value: Any) -> str:
    normalized = optional_string(value)
    if normalized in {"data_ready", "completed", "archived", "completed_with_warnings"}:
        return "READY"
    if normalized:
        return normalized.upper()
    return "ACCEPTED"


def normalize_memo_report_job_status(value: Any) -> str:
    normalized = optional_string(value)
    if normalized == "archived":
        return "ARCHIVED"
    return normalize_report_job_status(value)


def as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def required_string(payload: dict[str, Any], key: str) -> str:
    normalized = optional_string(payload.get(key))
    if normalized is None:
        raise LotusReportRequestMappingError("LOTUS_REPORT_REQUEST_UNAVAILABLE")
    return normalized


def optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def bounded_identity(value: Any, *, default: str) -> str:
    normalized = optional_string(value)
    if (
        normalized is None
        or len(normalized) > MAX_CORRELATION_ID_LENGTH
        or any(ord(char) < 32 or ord(char) == 127 for char in normalized)
    ):
        return default
    return normalized
