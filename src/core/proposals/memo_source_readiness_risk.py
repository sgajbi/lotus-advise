from __future__ import annotations

from typing import Any

from src.core.proposals.source_readiness_common import (
    ReadinessStatus,
    source_readiness_section,
)


def build_risk_memo_source_sections(risk_lens: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        source_readiness_section(
            key="risk_concentration",
            owner_service="lotus-risk",
            status=_risk_concentration_status(risk_lens),
            evidence_refs=[
                "risk_lens.single_position_concentration",
                "risk_lens.issuer_concentration",
            ],
            missing_evidence=_risk_concentration_missing(risk_lens),
            reason_codes=_risk_concentration_reasons(risk_lens),
        ),
        source_readiness_section(
            key="risk_drawdown_stress_liquidity_private_assets_climate_geopolitical",
            owner_service="lotus-risk",
            status="PENDING_REVIEW",
            evidence_refs=["risk_lens"],
            missing_evidence=[
                "drawdown",
                "stress",
                "liquidity",
                "private_asset_exposure",
                "climate_geopolitical_exposure",
            ],
            reason_codes=["RISK_OWNER_EXTENDED_MEMO_EVIDENCE_NOT_PROVIDED"],
        ),
    ]


def _risk_concentration_status(risk_lens: dict[str, Any]) -> ReadinessStatus:
    if risk_lens.get("source_service") != "lotus-risk":
        return "PENDING_REVIEW"
    if isinstance(risk_lens.get("single_position_concentration"), dict) and isinstance(
        risk_lens.get("issuer_concentration"), dict
    ):
        return "READY"
    return "PENDING_REVIEW"


def _risk_concentration_missing(risk_lens: dict[str, Any]) -> list[str]:
    missing = []
    if risk_lens.get("source_service") != "lotus-risk":
        missing.append("lotus-risk source_service")
    if not isinstance(risk_lens.get("single_position_concentration"), dict):
        missing.append("single_position_concentration")
    if not isinstance(risk_lens.get("issuer_concentration"), dict):
        missing.append("issuer_concentration")
    return missing


def _risk_concentration_reasons(risk_lens: dict[str, Any]) -> list[str]:
    if not _risk_concentration_missing(risk_lens):
        return []
    return ["RISK_CONCENTRATION_SOURCE_EVIDENCE_INCOMPLETE"]


__all__ = ["build_risk_memo_source_sections"]
