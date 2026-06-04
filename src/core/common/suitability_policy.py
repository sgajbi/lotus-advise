from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Dict

from src.core.simulation_state_models import SimulatedState

STATUS_SORT = {"NEW": 0, "PERSISTENT": 1, "RESOLVED": 2}
SEVERITY_SORT = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"
EPSILON = Decimal("0.0000001")


@dataclass(frozen=True)
class IssueCandidate:
    issue_key: str
    issue_id: str
    dimension: str
    severity: str
    summary: str
    details: Dict[str, str]
    classification: str
    remediation: str | None = None
    approval_implication: str | None = None


@dataclass(frozen=True)
class _SuitabilityPolicyPack:
    pack_id: str
    version: str
    state_evaluators: tuple[Callable[..., None], ...]
    post_evaluators: tuple[Callable[..., None], ...]


def to_instrument_weight_map(state: SimulatedState) -> Dict[str, Decimal]:
    return {
        metric.key: metric.weight for metric in state.allocation_by_instrument if metric.weight > 0
    }


def to_cash_weight(state: SimulatedState) -> Decimal:
    return next(
        (metric.weight for metric in state.allocation_by_asset_class if metric.key == "CASH"),
        Decimal("0"),
    )


def severity_for_concentration(measured: Decimal, limit: Decimal) -> str:
    if measured > (limit * Decimal("1.25")):
        return HIGH
    return MEDIUM


def issue_data_quality(
    *,
    issue_key: str,
    summary: str,
    details: Dict[str, str],
    severity: str,
) -> IssueCandidate:
    return IssueCandidate(
        issue_key=issue_key,
        issue_id="SUIT_DATA_QUALITY",
        dimension="DATA_QUALITY",
        severity=severity,
        summary=summary,
        details=details,
        classification="UNKNOWN_DUE_TO_MISSING_EVIDENCE",
        remediation="Refresh the missing upstream enrichment before progressing the proposal.",
        approval_implication="DATA_REMEDIATION",
    )
