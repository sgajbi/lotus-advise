from typing import Any

from src.core.engine_options_models import EngineOptions
from src.core.portfolio_models import ShelfEntry
from src.core.simulation_state_models import SimulatedState
from src.core.suitability_models import (
    SuitabilityEvidence,
    SuitabilityEvidenceSnapshotIds,
    SuitabilityIssue,
    SuitabilityResult,
    SuitabilitySummary,
)

from .suitability_policy import IssueCandidate, _SuitabilityPolicyPack
from .suitability_post_trade_issues import (
    append_governance_trade_attempt_issues,
    append_product_complexity_issues,
    append_restricted_product_mandate_context_issues,
)
from .suitability_projection import (
    classify_issues,
    highest_new_issue_severity,
    recommended_gate,
)
from .suitability_state_issues import (
    evaluate_cash_band_issue,
    evaluate_governance_holdings_issues,
    evaluate_issuer_issues,
    evaluate_liquidity_issues,
    evaluate_single_position_issues,
    scan_state_issues,
)


def compute_suitability_result(
    *,
    before: SimulatedState,
    after: SimulatedState,
    shelf: list[ShelfEntry],
    options: EngineOptions,
    portfolio_snapshot_id: str,
    market_data_snapshot_id: str,
    evidence_as_of: str | None = None,
    proposed_trades: list[Any] | None = None,
    policy_context: dict[str, Any] | None = None,
) -> SuitabilityResult:
    policy_pack = _GLOBAL_PRIVATE_BANKING_BASELINE_PACK
    shelf_by_instrument = shelf_index(shelf)
    before_issues, after_issues = scan_before_after_issues(
        before=before,
        after=after,
        shelf_by_instrument=shelf_by_instrument,
        options=options,
        policy_pack=policy_pack,
    )
    append_post_trade_issues(
        before=before,
        after=after,
        after_issues=after_issues,
        shelf_by_instrument=shelf_by_instrument,
        proposed_trades=proposed_trades or [],
        options=options,
        policy_context=policy_context,
        policy_pack=policy_pack,
    )
    issues = classify_issues(
        before_issues=before_issues,
        after_issues=after_issues,
        evidence=suitability_evidence(
            evidence_as_of=evidence_as_of,
            portfolio_snapshot_id=portfolio_snapshot_id,
            market_data_snapshot_id=market_data_snapshot_id,
        ),
        policy_pack=policy_pack,
    )
    return SuitabilityResult(
        summary=suitability_summary(issues),
        issues=issues,
        policy_pack_id=policy_pack.pack_id,
        policy_version=policy_pack.version,
        recommended_gate=recommended_gate(issues),
    )


def shelf_index(shelf: list[ShelfEntry]) -> dict[str, ShelfEntry]:
    return {entry.instrument_id: entry for entry in shelf}


def scan_before_after_issues(
    *,
    before: SimulatedState,
    after: SimulatedState,
    shelf_by_instrument: dict[str, ShelfEntry],
    options: EngineOptions,
    policy_pack: _SuitabilityPolicyPack,
) -> tuple[dict[str, IssueCandidate], dict[str, IssueCandidate]]:
    before_issues = scan_state_issues(
        target_state=before,
        before_state=before,
        shelf_by_instrument=shelf_by_instrument,
        options=options,
        policy_pack=policy_pack,
    )
    after_issues = scan_state_issues(
        target_state=after,
        before_state=before,
        shelf_by_instrument=shelf_by_instrument,
        options=options,
        policy_pack=policy_pack,
    )
    return before_issues, after_issues


def append_post_trade_issues(
    *,
    before: SimulatedState,
    after: SimulatedState,
    after_issues: dict[str, IssueCandidate],
    shelf_by_instrument: dict[str, ShelfEntry],
    proposed_trades: list[Any],
    options: EngineOptions,
    policy_context: dict[str, Any] | None,
    policy_pack: _SuitabilityPolicyPack,
) -> None:
    for evaluator in policy_pack.post_evaluators:
        evaluator(
            after_issues=after_issues,
            before=before,
            after=after,
            shelf_by_instrument=shelf_by_instrument,
            proposed_trades=proposed_trades,
            options=options,
            policy_context=policy_context,
        )


def suitability_evidence(
    *,
    evidence_as_of: str | None,
    portfolio_snapshot_id: str,
    market_data_snapshot_id: str,
) -> SuitabilityEvidence:
    return SuitabilityEvidence(
        as_of=evidence_as_of or market_data_snapshot_id,
        snapshot_ids=SuitabilityEvidenceSnapshotIds(
            portfolio_snapshot_id=portfolio_snapshot_id,
            market_data_snapshot_id=market_data_snapshot_id,
        ),
    )


def suitability_summary(issues: list[SuitabilityIssue]) -> SuitabilitySummary:
    new_issues = issues_with_status(issues, "NEW")
    return SuitabilitySummary(
        new_count=len(new_issues),
        resolved_count=len(issues_with_status(issues, "RESOLVED")),
        persistent_count=len(issues_with_status(issues, "PERSISTENT")),
        highest_severity_new=highest_new_issue_severity(new_issues),
    )


def issues_with_status(
    issues: list[SuitabilityIssue], status_change: str
) -> list[SuitabilityIssue]:
    return [issue for issue in issues if issue.status_change == status_change]


_GLOBAL_PRIVATE_BANKING_BASELINE_PACK = _SuitabilityPolicyPack(
    pack_id="global-private-banking-baseline",
    version="enterprise-suitability-policy.2026-04",
    state_evaluators=(
        evaluate_single_position_issues,
        evaluate_issuer_issues,
        evaluate_liquidity_issues,
        evaluate_governance_holdings_issues,
        evaluate_cash_band_issue,
    ),
    post_evaluators=(
        append_governance_trade_attempt_issues,
        append_product_complexity_issues,
        append_restricted_product_mandate_context_issues,
    ),
)
