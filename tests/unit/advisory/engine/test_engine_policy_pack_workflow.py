from __future__ import annotations

import pytest

from src.core.policy_packs import (
    PolicyEvaluationSignOffDecisionRequest,
    activate_policy_pack_version,
    finalize_policy_evaluation_record,
    get_policy_evaluation_workflow,
    get_policy_pack_version,
    record_policy_evaluation_sign_off_decision,
    reset_policy_evaluation_store_for_tests,
    reset_policy_pack_catalog_for_tests,
    validate_policy_pack_version,
)
from src.core.proposals.exceptions import ProposalValidationError


def setup_function() -> None:
    reset_policy_pack_catalog_for_tests()
    reset_policy_evaluation_store_for_tests()


def _base_evidence_bundle() -> dict:
    return {
        "context_resolution": {
            "advisory_policy_context": {
                "jurisdiction": "SG",
                "client_classification": "ACCREDITED_INVESTOR",
                "booking_center_code": "SG",
                "household_id": "HH-PB-001",
                "account_id": "ACCT-PB-001",
                "time_horizon": "5Y",
                "liquidity_need": "MEDIUM",
                "mandate_id": "MANDATE-BALANCED-001",
                "objectives": ["capital_preservation", "balanced_growth"],
                "restrictions": ["no_single_name_above_10pct"],
            }
        },
        "inputs": {
            "portfolio_snapshot": {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "positions": [{"instrument_id": "US_EQ_ETF", "quantity": "100"}],
                "cash_balances": [{"currency": "USD", "amount": "50000"}],
            },
            "market_data_snapshot": {
                "prices": [{"instrument_id": "US_EQ_ETF", "price": "100", "currency": "USD"}],
                "fx_rates": [{"pair": "USD/SGD", "rate": "1.35"}],
            },
            "shelf_entries": [
                {
                    "instrument_id": "SG_STRUCTURED_NOTE",
                    "eligibility": {"jurisdictions": ["SG"]},
                    "target_market": {"client_segments": ["ACCREDITED_INVESTOR"]},
                    "complexity": "COMPLEX",
                    "structured_product": True,
                }
            ],
            "proposed_trades": [{"instrument_id": "SG_STRUCTURED_NOTE", "side": "BUY"}],
        },
        "risk_lens": {
            "source_service": "lotus-risk",
            "single_position_concentration": {"top_position_weight_current": "0.10"},
            "issuer_concentration": {"hhi_current": "1200"},
            "drawdown": {"max_drawdown_1y": "0.08"},
            "var": {"var_95_1m": "0.04"},
            "stress": {"equity_down_20": "-0.09"},
            "liquidity_risk": {"days_to_liquidate": "3"},
            "private_asset_risk": {"private_asset_weight": "0.00"},
            "climate_geopolitical_risk": {"status": "not_material"},
        },
        "artifact": {
            "assumptions_and_limits": {
                "costs_and_fees": {"included": True},
                "tax": {"included": True},
                "execution": {"included": True},
            },
            "disclosures": {
                "product_docs": [{"instrument_id": "SG_STRUCTURED_NOTE", "doc_ref": "Term sheet"}],
            },
        },
        "conflict_evidence": {"material_conflict": False, "review_ref": "conflict-review-001"},
    }


def _activate_sg_policy_pack() -> None:
    detail = get_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    )
    validate_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        requested_by="policy_steward_1",
        idempotency_key="validate-sg-workflow",
        reason={"purpose": "slice 9 workflow test"},
    )
    activate_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        activated_by="policy_checker_1",
        source_content_hash=detail.policy_pack.content_hash,
        idempotency_key="activate-sg-workflow",
        reason={"purpose": "slice 9 workflow test"},
    )


def _create_policy_evaluation(*, material_conflict: bool = False):
    _activate_sg_policy_pack()
    evidence = _base_evidence_bundle()
    evidence["conflict_evidence"]["material_conflict"] = material_conflict
    return finalize_policy_evaluation_record(
        evidence_bundle=evidence,
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        proposal_id="pp_policy_workflow",
        proposal_version_id="ppv_policy_workflow",
        created_by="advisor_1",
        idempotency_key=f"policy-workflow-{material_conflict}",
        reason={"purpose": "workflow projection"},
    ).record


def test_policy_workflow_projects_open_approval_disclosure_consent_and_sla_posture() -> None:
    record = _create_policy_evaluation()
    workflow = get_policy_evaluation_workflow(evaluation_id=record.evaluation_id)

    assert workflow.sign_off_status == "PENDING_REVIEW"
    assert workflow.client_ready_publication == "BLOCKED"
    assert workflow.approval_dependencies[0].requirement_id == (
        "REVIEW_DISCLOSURE:SG_STRUCTURED_NOTE"
    )
    assert workflow.approval_dependencies[0].owner_role == "INVESTMENT_COUNSELLOR"
    assert workflow.disclosure_requirements[0].status == "OPEN"
    assert workflow.consent_requirements[0].status == "OPEN"
    assert workflow.sla_posture["open_requirement_count"] == 5
    assert workflow.conflict_posture["status"] == "SATISFIED"


def test_policy_sign_off_requires_maker_checker_and_all_requirements_resolved() -> None:
    record = _create_policy_evaluation()

    with pytest.raises(ProposalValidationError, match="MAKER_CHECKER"):
        record_policy_evaluation_sign_off_decision(
            evaluation_id=record.evaluation_id,
            payload=PolicyEvaluationSignOffDecisionRequest(
                actor_id="advisor_1",
                decision="APPROVE_FOR_POLICY_SIGN_OFF",
                source_evaluation_hash=record.evaluation_hash,
            ),
        )

    with pytest.raises(ProposalValidationError, match="REQUIREMENTS_OPEN"):
        record_policy_evaluation_sign_off_decision(
            evaluation_id=record.evaluation_id,
            payload=PolicyEvaluationSignOffDecisionRequest(
                actor_id="policy_checker_1",
                decision="APPROVE_FOR_POLICY_SIGN_OFF",
                source_evaluation_hash=record.evaluation_hash,
            ),
        )

    response = record_policy_evaluation_sign_off_decision(
        evaluation_id=record.evaluation_id,
        payload=PolicyEvaluationSignOffDecisionRequest(
            actor_id="policy_checker_1",
            decision="APPROVE_FOR_POLICY_SIGN_OFF",
            source_evaluation_hash=record.evaluation_hash,
            resolved_approval_dependencies=record.approval_dependencies,
            satisfied_disclosure_requirements=record.disclosure_requirements,
            satisfied_consent_requirements=record.consent_requirements,
            reason={"purpose": "all requirements reviewed"},
        ),
        idempotency_key="policy-sign-off-decision-001",
    )

    assert response.workflow.sign_off_status == "SIGNED_OFF"
    assert response.workflow.sign_off_blockers == []
    assert response.sign_off_event.event_type == "POLICY_EVALUATION_SIGN_OFF_RECORDED"
    assert response.replay_metadata["client_ready_publication"] == "BLOCKED"


def test_policy_sign_off_rejection_does_not_satisfy_requirements() -> None:
    record = _create_policy_evaluation()

    response = record_policy_evaluation_sign_off_decision(
        evaluation_id=record.evaluation_id,
        payload=PolicyEvaluationSignOffDecisionRequest(
            actor_id="policy_checker_1",
            decision="REQUEST_MORE_EVIDENCE",
            source_evaluation_hash=record.evaluation_hash,
            resolved_approval_dependencies=record.approval_dependencies,
            satisfied_disclosure_requirements=record.disclosure_requirements,
            satisfied_consent_requirements=record.consent_requirements,
            reason={"purpose": "missing documented consent evidence"},
        ),
        idempotency_key="policy-sign-off-request-more-evidence-001",
    )

    assert response.sign_off_event.event_type == "POLICY_EVALUATION_REVIEW_RECORDED"
    assert response.workflow.sign_off_status == "PENDING_REVIEW"
    assert response.workflow.sla_posture["open_requirement_count"] == 5
    assert response.workflow.approval_dependencies[0].status == "OPEN"
    assert response.workflow.disclosure_requirements[0].status == "OPEN"
    assert response.workflow.consent_requirements[0].status == "OPEN"


def test_policy_sign_off_blocks_material_conflict_until_review_outcome_is_recorded() -> None:
    record = _create_policy_evaluation(material_conflict=True)
    workflow = get_policy_evaluation_workflow(evaluation_id=record.evaluation_id)

    assert workflow.conflict_posture["status"] == "BLOCKED"
    assert workflow.sign_off_status == "BLOCKED"

    with pytest.raises(ProposalValidationError, match="REQUIREMENTS_OPEN"):
        record_policy_evaluation_sign_off_decision(
            evaluation_id=record.evaluation_id,
            payload=PolicyEvaluationSignOffDecisionRequest(
                actor_id="policy_checker_1",
                decision="APPROVE_FOR_POLICY_SIGN_OFF",
                source_evaluation_hash=record.evaluation_hash,
                conflict_review_outcome="NO_MATERIAL_CONFLICT_REMAINING",
            ),
        )
