from __future__ import annotations

from typing import Any

from src.core.proposals.source_readiness_common import (
    ReadinessStatus,
    source_readiness_section,
)


def build_advise_memo_source_sections(
    *,
    proposal_result: dict[str, Any],
    proposed_trades: list[Any],
    proposed_cash_flows: list[Any],
) -> list[dict[str, Any]]:
    return [
        source_readiness_section(
            key="advise_decision_summary",
            owner_service="lotus-advise",
            status=(
                "READY"
                if isinstance(proposal_result.get("proposal_decision_summary"), dict)
                else "PENDING_REVIEW"
            ),
            evidence_refs=["engine_outputs.proposal_result.proposal_decision_summary"],
            missing_evidence=(
                []
                if isinstance(proposal_result.get("proposal_decision_summary"), dict)
                else ["proposal_decision_summary"]
            ),
            reason_codes=(
                []
                if isinstance(proposal_result.get("proposal_decision_summary"), dict)
                else ["ADVISE_DECISION_SUMMARY_NOT_CAPTURED"]
            ),
        ),
        source_readiness_section(
            key="advise_alternatives_lifecycle_execution_boundary",
            owner_service="lotus-advise",
            status=_advise_boundary_status(
                proposal_result=proposal_result,
                proposed_trades=proposed_trades,
                proposed_cash_flows=proposed_cash_flows,
            ),
            evidence_refs=[
                "engine_outputs.proposal_result.proposal_alternatives",
                "engine_outputs.proposal_result.gate_decision",
                "inputs.proposed_trades",
                "inputs.proposed_cash_flows",
            ],
            missing_evidence=_advise_boundary_missing(proposal_result),
            reason_codes=_advise_boundary_reasons(proposal_result),
        ),
    ]


def _advise_boundary_status(
    *,
    proposal_result: dict[str, Any],
    proposed_trades: list[Any],
    proposed_cash_flows: list[Any],
) -> ReadinessStatus:
    has_gate = isinstance(proposal_result.get("gate_decision"), dict)
    has_activity = bool(proposed_trades or proposed_cash_flows)
    has_alternatives = isinstance(proposal_result.get("proposal_alternatives"), dict)
    if has_gate and (has_alternatives or has_activity):
        return "READY"
    return "PENDING_REVIEW"


def _advise_boundary_missing(proposal_result: dict[str, Any]) -> list[str]:
    missing = []
    if not isinstance(proposal_result.get("gate_decision"), dict):
        missing.append("gate_decision")
    if not isinstance(proposal_result.get("proposal_alternatives"), dict):
        missing.append("proposal_alternatives")
    return missing


def _advise_boundary_reasons(proposal_result: dict[str, Any]) -> list[str]:
    missing = _advise_boundary_missing(proposal_result)
    if not missing:
        return []
    return [f"ADVISE_{item.upper()}_NOT_CAPTURED" for item in missing]


__all__ = ["build_advise_memo_source_sections"]
