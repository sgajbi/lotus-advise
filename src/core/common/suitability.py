from typing import Any

from src.core.engine_options_models import EngineOptions
from src.core.portfolio_models import ShelfEntry
from src.core.simulation_state_models import SimulatedState
from src.core.suitability_models import (
    SuitabilityEvidence,
    SuitabilityEvidenceSnapshotIds,
    SuitabilityResult,
    SuitabilitySummary,
)

from .suitability_policy import _SuitabilityPolicyPack
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
    shelf_by_instrument = {entry.instrument_id: entry for entry in shelf}
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
    for evaluator in policy_pack.post_evaluators:
        evaluator(
            after_issues=after_issues,
            before=before,
            after=after,
            shelf_by_instrument=shelf_by_instrument,
            proposed_trades=proposed_trades or [],
            options=options,
            policy_context=policy_context,
        )

    evidence = SuitabilityEvidence(
        as_of=evidence_as_of or market_data_snapshot_id,
        snapshot_ids=SuitabilityEvidenceSnapshotIds(
            portfolio_snapshot_id=portfolio_snapshot_id,
            market_data_snapshot_id=market_data_snapshot_id,
        ),
    )

    issues = classify_issues(
        before_issues=before_issues,
        after_issues=after_issues,
        evidence=evidence,
        policy_pack=policy_pack,
    )

    new_issues = [issue for issue in issues if issue.status_change == "NEW"]
    resolved_issues = [issue for issue in issues if issue.status_change == "RESOLVED"]
    persistent_issues = [issue for issue in issues if issue.status_change == "PERSISTENT"]

    return SuitabilityResult(
        summary=SuitabilitySummary(
            new_count=len(new_issues),
            resolved_count=len(resolved_issues),
            persistent_count=len(persistent_issues),
            highest_severity_new=highest_new_issue_severity(new_issues),
        ),
        issues=issues,
        policy_pack_id=policy_pack.pack_id,
        policy_version=policy_pack.version,
        recommended_gate=recommended_gate(issues),
    )


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
