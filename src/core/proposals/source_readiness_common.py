from __future__ import annotations

from typing import Any, Literal

ReadinessStatus = Literal["READY", "PENDING_REVIEW", "BLOCKED", "NOT_AVAILABLE"]


def dict_at(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def list_at(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def source_readiness_section(
    *,
    key: str,
    owner_service: str,
    status: ReadinessStatus,
    evidence_refs: list[str],
    missing_evidence: list[str],
    reason_codes: list[str],
) -> dict[str, Any]:
    return {
        "key": key,
        "owner_service": owner_service,
        "status": status,
        "evidence_refs": evidence_refs,
        "missing_evidence": missing_evidence,
        "reason_codes": reason_codes,
    }


def overall_posture(sections: list[dict[str, Any]]) -> ReadinessStatus:
    statuses = {section["status"] for section in sections}
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if "PENDING_REVIEW" in statuses:
        return "PENDING_REVIEW"
    if "READY" in statuses:
        return "READY"
    return "NOT_AVAILABLE"


def source_authority(sections: list[dict[str, Any]]) -> dict[str, Any]:
    authority: dict[str, Any] = {}
    for section in sections:
        owner = section["owner_service"]
        authority.setdefault(owner, {"section_keys": [], "ready_section_keys": []})
        authority[owner]["section_keys"].append(section["key"])
        if section["status"] == "READY":
            authority[owner]["ready_section_keys"].append(section["key"])
    return authority
