from __future__ import annotations

from typing import Any

from src.integrations.lotus_report.request_mapping import optional_string

_PORTFOLIO_REVIEW_READY = {
    "archived",
    "completed",
    "completed_with_warnings",
    "data_ready",
}
_REPORT_PACKAGE_READY = {"archived"}
_REPORT_JOB_FAILED = {
    "archive_failed",
    "cancelled",
    "canceled",
    "failed",
    "rejected",
    "render_failed",
}
_REPORT_PACKAGE_PENDING_ARCHIVE = {
    "completed",
    "completed_with_warnings",
    "data_ready",
    "rendered",
}
_REPORT_STATUS_UNAVAILABLE = "report_status_unavailable"
_REPORT_STATUS_INVALID = "report_status_invalid"


def normalize_portfolio_review_status(value: Any) -> str:
    normalized = _provider_status(value)
    if normalized in _PORTFOLIO_REVIEW_READY:
        return "READY"
    if normalized in _REPORT_JOB_FAILED:
        return "FAILED"
    if normalized == _REPORT_STATUS_UNAVAILABLE:
        return "REPORT_STATUS_UNAVAILABLE"
    if normalized == _REPORT_STATUS_INVALID:
        return "REPORT_STATUS_INVALID"
    return normalized.upper() if normalized else "ACCEPTED"


def normalize_report_package_status(value: Any) -> str:
    normalized = _provider_status(value)
    if normalized in _REPORT_PACKAGE_READY:
        return "ARCHIVED"
    if normalized in _REPORT_JOB_FAILED:
        return "FAILED"
    if normalized in _REPORT_PACKAGE_PENDING_ARCHIVE:
        return "PENDING_ARCHIVE"
    if normalized == _REPORT_STATUS_UNAVAILABLE:
        return "REPORT_STATUS_UNAVAILABLE"
    if normalized == _REPORT_STATUS_INVALID:
        return "REPORT_STATUS_INVALID"
    return normalized.upper() if normalized else "ACCEPTED"


def is_report_package_terminal_status(value: Any) -> bool:
    normalized = _provider_status(value)
    return normalized in _REPORT_PACKAGE_READY or normalized in _REPORT_JOB_FAILED


def _provider_status(value: Any) -> str | None:
    normalized = optional_string(value)
    return normalized.lower() if normalized else None
