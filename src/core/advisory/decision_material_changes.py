from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from src.core.advisory.decision_summary_models import (
    ProposalDecisionApprovalRequirement,
    ProposalDecisionMaterialChange,
    ProposalDecisionMissingEvidence,
)
from src.core.models import AllocationMetric, ProposalResult, SimulatedState

_ZERO = Decimal("0")
_ASSET_CLASS_DELTA_THRESHOLD = Decimal("0.05")
_CASH_DELTA_THRESHOLD = Decimal("0.03")
_CURRENCY_DELTA_THRESHOLD = Decimal("0.05")
_TOP_POSITION_DELTA_THRESHOLD = Decimal("0.05")
_ISSUER_HHI_DELTA_THRESHOLD = Decimal("500")


def build_material_changes(
    *,
    result: ProposalResult,
    approval_requirements: list[ProposalDecisionApprovalRequirement],
    missing_evidence: list[ProposalDecisionMissingEvidence],
) -> list[ProposalDecisionMaterialChange]:
    changes: list[ProposalDecisionMaterialChange] = []
    changes.extend(_build_asset_class_changes(result))
    changes.extend(_build_cash_changes(result))
    changes.extend(_build_currency_changes(result))
    changes.extend(_build_concentration_changes(result))
    changes.extend(_build_product_and_mandate_changes(result))
    changes.extend(_build_data_quality_changes(missing_evidence))
    changes.extend(_build_approval_change(approval_requirements))
    return sorted(
        changes,
        key=lambda item: (_severity_rank(item.severity), item.family, item.change_id),
    )


def _build_asset_class_changes(result: ProposalResult) -> list[ProposalDecisionMaterialChange]:
    before = _weight_map(result.before.allocation_by_asset_class)
    after = _weight_map(result.after_simulated.allocation_by_asset_class)
    changes: list[ProposalDecisionMaterialChange] = []
    for asset_class in sorted(set(before) | set(after)):
        if asset_class == "CASH":
            continue
        before_weight = before.get(asset_class, _ZERO)
        after_weight = after.get(asset_class, _ZERO)
        delta = after_weight - before_weight
        if abs(delta) < _ASSET_CLASS_DELTA_THRESHOLD:
            continue
        changes.append(
            ProposalDecisionMaterialChange(
                change_id=f"asset-class:{asset_class}",
                family="ALLOCATION_CHANGE",
                severity=_delta_severity(
                    delta, medium=_ASSET_CLASS_DELTA_THRESHOLD, high=Decimal("0.10")
                ),
                before={"asset_class": asset_class, "weight": _weight_str(before_weight)},
                after={"asset_class": asset_class, "weight": _weight_str(after_weight)},
                delta={"weight": _weight_str(delta)},
                threshold={"material_delta": _weight_str(_ASSET_CLASS_DELTA_THRESHOLD)},
                summary=(
                    f"Asset-class allocation for {asset_class} changed from "
                    f"{_pct_str(before_weight)} to {_pct_str(after_weight)}."
                ),
                evidence_refs=[
                    "proposal.before.allocation_by_asset_class",
                    "proposal.after_simulated.allocation_by_asset_class",
                ],
            )
        )
    return changes


def _build_cash_changes(result: ProposalResult) -> list[ProposalDecisionMaterialChange]:
    before_weight = _cash_weight(result.before)
    after_weight = _cash_weight(result.after_simulated)
    delta = after_weight - before_weight
    if abs(delta) < _CASH_DELTA_THRESHOLD:
        return []
    return [
        ProposalDecisionMaterialChange(
            change_id="cash-weight",
            family="CASH_CHANGE",
            severity=_delta_severity(delta, medium=_CASH_DELTA_THRESHOLD, high=Decimal("0.10")),
            before={"weight": _weight_str(before_weight)},
            after={"weight": _weight_str(after_weight)},
            delta={"weight": _weight_str(delta)},
            threshold={"material_delta": _weight_str(_CASH_DELTA_THRESHOLD)},
            summary=(
                f"Cash allocation changed from {_pct_str(before_weight)} "
                f"to {_pct_str(after_weight)}."
            ),
            evidence_refs=[
                "proposal.before.allocation_by_asset_class",
                "proposal.after_simulated.allocation_by_asset_class",
            ],
        )
    ]


def _build_currency_changes(result: ProposalResult) -> list[ProposalDecisionMaterialChange]:
    before = _currency_weight_map(result.before)
    after = _currency_weight_map(result.after_simulated)
    changes: list[ProposalDecisionMaterialChange] = []
    for currency in sorted(set(before) | set(after)):
        before_weight = before.get(currency, _ZERO)
        after_weight = after.get(currency, _ZERO)
        delta = after_weight - before_weight
        if abs(delta) < _CURRENCY_DELTA_THRESHOLD:
            continue
        changes.append(
            ProposalDecisionMaterialChange(
                change_id=f"currency:{currency}",
                family="CURRENCY_EXPOSURE_CHANGE",
                severity=_delta_severity(
                    delta, medium=_CURRENCY_DELTA_THRESHOLD, high=Decimal("0.10")
                ),
                before={"currency": currency, "weight": _weight_str(before_weight)},
                after={"currency": currency, "weight": _weight_str(after_weight)},
                delta={"weight": _weight_str(delta)},
                threshold={"material_delta": _weight_str(_CURRENCY_DELTA_THRESHOLD)},
                summary=(
                    f"Currency exposure for {currency} changed from "
                    f"{_pct_str(before_weight)} to {_pct_str(after_weight)}."
                ),
                evidence_refs=["proposal.before.positions", "proposal.after_simulated.positions"],
            )
        )
    return changes


def _build_concentration_changes(result: ProposalResult) -> list[ProposalDecisionMaterialChange]:
    risk_lens = result.explanation.get("risk_lens")
    if not isinstance(risk_lens, dict):
        return []
    changes: list[ProposalDecisionMaterialChange] = []
    single = risk_lens.get("single_position_concentration")
    if isinstance(single, dict):
        delta = _decimal(single.get("top_position_weight_delta"))
        if abs(delta) >= _TOP_POSITION_DELTA_THRESHOLD:
            changes.append(
                ProposalDecisionMaterialChange(
                    change_id="concentration:top-position",
                    family="CONCENTRATION_CHANGE",
                    severity=_delta_severity(
                        delta, medium=_TOP_POSITION_DELTA_THRESHOLD, high=Decimal("0.10")
                    ),
                    before={"weight": str(single.get("top_position_weight_current"))},
                    after={"weight": str(single.get("top_position_weight_proposed"))},
                    delta={"weight": str(single.get("top_position_weight_delta"))},
                    threshold={"material_delta": _weight_str(_TOP_POSITION_DELTA_THRESHOLD)},
                    summary="Top position concentration changed materially in the risk lens.",
                    evidence_refs=["proposal.explanation.risk_lens.single_position_concentration"],
                )
            )
    issuer = risk_lens.get("issuer_concentration")
    if isinstance(issuer, dict):
        hhi_delta = _decimal(issuer.get("hhi_delta"))
        if abs(hhi_delta) >= _ISSUER_HHI_DELTA_THRESHOLD:
            changes.append(
                ProposalDecisionMaterialChange(
                    change_id="concentration:issuer-hhi",
                    family="CONCENTRATION_CHANGE",
                    severity=_delta_severity(
                        hhi_delta,
                        medium=_ISSUER_HHI_DELTA_THRESHOLD,
                        high=Decimal("1000"),
                    ),
                    before={"hhi": str(issuer.get("hhi_current"))},
                    after={"hhi": str(issuer.get("hhi_proposed"))},
                    delta={"hhi": str(issuer.get("hhi_delta"))},
                    threshold={"material_hhi_delta": str(_ISSUER_HHI_DELTA_THRESHOLD)},
                    summary="Issuer concentration changed materially in the risk lens.",
                    evidence_refs=["proposal.explanation.risk_lens.issuer_concentration"],
                )
            )
    return changes


def _build_product_and_mandate_changes(
    result: ProposalResult,
) -> list[ProposalDecisionMaterialChange]:
    if result.suitability is None:
        return []
    changes: list[ProposalDecisionMaterialChange] = []
    for issue in result.suitability.issues:
        if issue.status_change not in {"NEW", "PERSISTENT"}:
            continue
        if issue.issue_id == "MISSING_CLIENT_PRODUCT_COMPLEXITY_EVIDENCE":
            changes.append(
                ProposalDecisionMaterialChange(
                    change_id=f"product-complexity:{issue.issue_key}",
                    family="PRODUCT_COMPLEXITY_CHANGE",
                    severity=issue.severity,
                    before={},
                    after=issue.details,
                    delta={"classification": issue.classification},
                    threshold={},
                    summary=issue.summary,
                    evidence_refs=[f"proposal.suitability.issues.{issue.issue_key}"],
                )
            )
        if issue.issue_id == "MISSING_MANDATE_RESTRICTED_PRODUCT_EVIDENCE":
            changes.append(
                ProposalDecisionMaterialChange(
                    change_id=f"mandate-alignment:{issue.issue_key}",
                    family="MANDATE_ALIGNMENT_CHANGE",
                    severity=issue.severity,
                    before={},
                    after=issue.details,
                    delta={"classification": issue.classification},
                    threshold={},
                    summary=issue.summary,
                    evidence_refs=[f"proposal.suitability.issues.{issue.issue_key}"],
                )
            )
    return changes


def _build_data_quality_changes(
    missing_evidence: list[ProposalDecisionMissingEvidence],
) -> list[ProposalDecisionMaterialChange]:
    changes: list[ProposalDecisionMaterialChange] = []
    for item in missing_evidence:
        if item.evidence_type not in {"MARKET_PRICE", "FX_RATE", "RISK_LENS"}:
            continue
        changes.append(
            ProposalDecisionMaterialChange(
                change_id=f"data-quality:{item.reason_code}",
                family="DATA_QUALITY_CHANGE",
                severity="HIGH" if item.blocking else "MEDIUM",
                before={},
                after={"evidence_type": item.evidence_type},
                delta={"blocking": item.blocking},
                threshold={},
                summary=item.summary,
                evidence_refs=item.evidence_refs,
            )
        )
    return changes


def _build_approval_change(
    approval_requirements: list[ProposalDecisionApprovalRequirement],
) -> list[ProposalDecisionMaterialChange]:
    if not approval_requirements:
        return []
    after_types = sorted({item.approval_type for item in approval_requirements})
    highest_severity = min(
        approval_requirements, key=lambda item: _severity_rank(item.severity)
    ).severity
    return [
        ProposalDecisionMaterialChange(
            change_id="approval-requirements",
            family="APPROVAL_REQUIREMENT_CHANGE",
            severity=highest_severity,
            before={"requirement_count": 0},
            after={"requirement_count": len(approval_requirements), "approval_types": after_types},
            delta={"introduced": after_types},
            threshold={},
            summary=(
                f"Proposal now requires {len(approval_requirements)} approval or remediation "
                "actions."
            ),
            evidence_refs=["proposal.gate_decision", "proposal.suitability"],
        )
    ]


def _weight_map(rows: Sequence[AllocationMetric]) -> dict[str, Decimal]:
    return {str(row.key): row.weight for row in rows}


def _cash_weight(state: SimulatedState) -> Decimal:
    for row in state.allocation_by_asset_class:
        if row.key == "CASH":
            return row.weight
    return _ZERO


def _currency_weight_map(state: SimulatedState) -> dict[str, Decimal]:
    if "currency" in state.allocation_by_attribute:
        return _weight_map(state.allocation_by_attribute["currency"])
    weights: dict[str, Decimal] = {}
    for position in state.positions:
        weights[position.instrument_currency] = (
            weights.get(position.instrument_currency, _ZERO) + position.weight
        )
    return weights


def _delta_severity(delta: Decimal, *, medium: Decimal, high: Decimal) -> str:
    absolute = abs(delta)
    if absolute >= high:
        return "HIGH"
    if absolute >= medium:
        return "MEDIUM"
    return "LOW"


def _severity_rank(severity: str) -> int:
    return {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[severity]


def _weight_str(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.0001")), "f")


def _pct_str(value: Decimal) -> str:
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%"


def _decimal(value: object) -> Decimal:
    if value is None:
        return _ZERO
    return Decimal(str(value))
