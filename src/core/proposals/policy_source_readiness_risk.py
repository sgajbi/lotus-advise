from __future__ import annotations

from typing import Any, cast

from src.core.proposals.source_readiness_common import (
    ReadinessStatus,
    dict_at,
    source_readiness_section,
)


def build_risk_policy_source_section(risk_lens: dict[str, Any]) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        source_readiness_section(
        key="risk_policy_metrics",
        owner_service="lotus-risk",
        status=_risk_policy_status(risk_lens),
        evidence_refs=[
            "risk_lens.single_position_concentration",
            "risk_lens.issuer_concentration",
            "risk_lens.drawdown",
            "risk_lens.var",
            "risk_lens.stress",
            "risk_lens.liquidity_risk",
            "risk_lens.private_asset_risk",
            "risk_lens.climate_geopolitical_risk",
        ],
        missing_evidence=_risk_policy_missing(risk_lens),
        reason_codes=_risk_policy_reasons(risk_lens),
        ),
    )


def _risk_policy_status(risk_lens: dict[str, Any]) -> ReadinessStatus:
    if risk_lens.get("source_service") != "lotus-risk":
        return "BLOCKED"
    if _risk_policy_degraded(risk_lens):
        return "PENDING_REVIEW"
    return "READY" if not _risk_policy_missing(risk_lens) else "PENDING_REVIEW"


def _risk_policy_missing(risk_lens: dict[str, Any]) -> list[str]:
    missing = []
    if risk_lens.get("source_service") != "lotus-risk":
        missing.append("lotus-risk source_service")
    if _risk_policy_degraded(risk_lens):
        missing.append("lotus-risk degraded policy metrics")
    for key in (
        "single_position_concentration",
        "issuer_concentration",
        "drawdown",
        "var",
        "stress",
        "liquidity_risk",
        "private_asset_risk",
        "climate_geopolitical_risk",
    ):
        if not isinstance(risk_lens.get(key), dict):
            missing.append(key)
    return missing


def _risk_policy_reasons(risk_lens: dict[str, Any]) -> list[str]:
    missing = _risk_policy_missing(risk_lens)
    if not missing:
        return []
    if "lotus-risk source_service" in missing:
        return ["RISK_OWNER_POLICY_EVIDENCE_NOT_AVAILABLE"]
    if "lotus-risk degraded policy metrics" in missing:
        return ["RISK_OWNER_POLICY_EVIDENCE_DEGRADED"]
    return ["RISK_OWNER_POLICY_EVIDENCE_INCOMPLETE"]


def _risk_policy_degraded(risk_lens: dict[str, Any]) -> bool:
    supportability = dict_at(risk_lens, "supportability")
    state = str(
        risk_lens.get("supportability_state")
        or risk_lens.get("state")
        or supportability.get("state")
        or supportability.get("status")
        or ""
    ).upper()
    return state in {"DEGRADED", "STALE", "PARTIAL"}
