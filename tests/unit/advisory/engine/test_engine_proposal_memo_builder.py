from copy import deepcopy

from src.core.proposals.memo_builder import build_advisory_proposal_memo_evidence_pack
from src.core.proposals.memo_models import ProposalMemoSectionKey
from src.core.proposals.memo_source_readiness import build_memo_source_readiness


def _evidence_bundle() -> dict:
    evidence = {
        "context_resolution": {
            "resolution_source": "LOTUS_CORE",
            "resolved_context": {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "portfolio_snapshot_id": "core-portfolio-snapshot-001",
                "market_data_snapshot_id": "core-market-data-snapshot-001",
            },
            "advisory_policy_context": {
                "context_source": "LOTUS_CORE",
                "household_id": "HH-PB-001",
                "mandate_id": "MANDATE-BALANCED-001",
                "jurisdiction": "SG",
            },
        },
        "inputs": {
            "portfolio_snapshot": {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "base_currency": "USD",
                "positions": [{"instrument_id": "US_EQ_ETF", "quantity": "100"}],
                "cash_balances": [{"currency": "USD", "amount": "50000"}],
            },
            "market_data_snapshot": {
                "prices": [
                    {
                        "instrument_id": "US_EQ_ETF",
                        "price": "100",
                        "currency": "USD",
                        "valid_to": "3999-12-31",
                    }
                ],
                "fx_rates": [{"pair": "USD/SGD", "rate": "1.35", "effective_to": "3999-12-31"}],
            },
            "shelf_entries": [
                {
                    "instrument_id": "US_EQ_ETF",
                    "eligibility": {"jurisdictions": ["SG"]},
                    "complexity": "NON_COMPLEX",
                }
            ],
            "proposed_trades": [{"instrument_id": "US_EQ_ETF", "side": "BUY"}],
            "proposed_cash_flows": [],
        },
        "engine_outputs": {
            "proposal_result": {
                "proposal_decision_summary": {
                    "primary_summary": "Deploy excess cash within mandate.",
                    "recommended_next_action": "DISCUSS_WITH_CLIENT",
                },
                "proposal_alternatives": {"alternatives": []},
                "gate_decision": {"gate": "CLIENT_CONSENT_REQUIRED"},
            }
        },
        "risk_lens": {
            "source_service": "lotus-risk",
            "single_position_concentration": {"top_position_weight_current": "0.10"},
            "issuer_concentration": {"hhi_current": "1200"},
        },
    }
    evidence["memo_source_readiness"] = build_memo_source_readiness(evidence)
    return evidence


def _artifact() -> dict:
    return {
        "artifact_id": "pa_memo_001",
        "status": "READY",
        "proposal_decision_summary": {
            "primary_summary": "Deploy excess cash within mandate.",
            "recommended_next_action": "DISCUSS_WITH_CLIENT",
            "suitability_posture": {"status": "AVAILABLE"},
        },
        "proposal_alternatives": {
            "alternatives": [
                {"alternative_id": "alt_selected", "selected": True},
                {"alternative_id": "alt_rejected", "selected": False},
            ]
        },
        "summary": {
            "objective_tags": ["CASH_DEPLOYMENT", "RISK_ALIGNMENT"],
            "recommended_next_step": "CLIENT_CONSENT",
        },
        "portfolio_impact": {"delta": {"largest_weight_changes": []}},
        "risk_lens": {
            "status": "AVAILABLE",
            "source_service": "lotus-risk",
            "summary": "Concentration remains reviewable after the proposal.",
        },
        "suitability_summary": {
            "status": "AVAILABLE",
            "new_issues": 0,
            "persistent_issues": 0,
            "resolved_issues": 1,
        },
        "gate_decision": {"gate": "CLIENT_CONSENT_REQUIRED"},
        "trades_and_funding": {"trade_list": [{"instrument_id": "US_EQ_ETF"}]},
    }


def _section(pack, section_id: ProposalMemoSectionKey):
    return next(section for section in pack.sections if section.section_id == section_id)


def test_memo_builder_is_deterministic_and_builds_all_required_sections() -> None:
    evidence = _evidence_bundle()
    artifact = _artifact()

    first = build_advisory_proposal_memo_evidence_pack(
        proposal_id="pp_memo_001",
        proposal_version_no=1,
        proposal_version_id="ppv_memo_001",
        artifact_json=artifact,
        evidence_bundle=evidence,
    )
    second = build_advisory_proposal_memo_evidence_pack(
        proposal_id="pp_memo_001",
        proposal_version_no=1,
        proposal_version_id="ppv_memo_001",
        artifact_json=deepcopy(artifact),
        evidence_bundle=deepcopy(evidence),
    )

    assert first.memo_hash == second.memo_hash
    assert first.memo_id == second.memo_id
    assert len(first.sections) == 17
    assert [section.section_id for section in first.sections] == [
        "EXECUTIVE_SUMMARY",
        "CLIENT_AND_HOUSEHOLD_CONTEXT",
        "ADVISORY_OBJECTIVE_AND_CONSTRAINTS",
        "RECOMMENDATION",
        "REJECTED_ALTERNATIVES",
        "PORTFOLIO_IMPACT",
        "RISK_AND_SCENARIO_CONTEXT",
        "SUITABILITY_AND_BEST_INTEREST",
        "FEES_COSTS_TAX_AND_FRICTIONS",
        "CONFLICTS_AND_DISCLOSURES",
        "APPROVALS_CONSENTS_AND_MAKER_CHECKER",
        "REPORT_ARCHIVE_AND_DELIVERY_READINESS",
        "EXECUTION_HANDOFF_BOUNDARY",
        "EVIDENCE_AND_LINEAGE_APPENDIX",
        "COMPLIANCE_APPENDIX",
        "OPERATIONS_APPENDIX",
        "SUPPORTABILITY_APPENDIX",
    ]
    assert first.supportability["persistence"] == "NOT_IMPLEMENTED"
    assert first.projection_policy["client_ready_publication"] == "BLOCKED"


def test_memo_builder_requires_source_refs_for_material_claims() -> None:
    pack = build_advisory_proposal_memo_evidence_pack(
        proposal_id="pp_memo_001",
        proposal_version_no=1,
        artifact_json=_artifact(),
        evidence_bundle=_evidence_bundle(),
    )

    recommendation = _section(pack, "RECOMMENDATION")
    assert recommendation.material_claims
    for section in pack.sections:
        for claim in section.material_claims:
            assert claim.text
            assert claim.evidence_refs
            assert claim.source_authority_refs
    assert "artifact.proposal_decision_summary" in recommendation.evidence_refs
    assert "lotus-advise:proposal_decision_summary" in recommendation.source_authority_refs


def test_memo_builder_blocks_report_archive_and_preserves_missing_source_evidence() -> None:
    evidence = _evidence_bundle()
    evidence["context_resolution"]["resolution_source"] = "DIRECT_REQUEST"
    evidence["inputs"]["portfolio_snapshot"]["positions"] = []
    evidence["memo_source_readiness"] = build_memo_source_readiness(evidence)

    pack = build_advisory_proposal_memo_evidence_pack(
        proposal_id="pp_memo_blocked",
        proposal_version_no=1,
        artifact_json=_artifact(),
        evidence_bundle=evidence,
    )

    assert pack.status == "BLOCKED"
    portfolio_impact = _section(pack, "PORTFOLIO_IMPACT")
    assert portfolio_impact.status == "BLOCKED"
    assert "positions" in portfolio_impact.missing_evidence
    assert "CORE_POSITIONS_NOT_PROVIDED" in portfolio_impact.reason_codes
    report_readiness = _section(pack, "REPORT_ARCHIVE_AND_DELIVERY_READINESS")
    assert report_readiness.status == "BLOCKED"
    assert "memo_report_package" in report_readiness.missing_evidence
    assert report_readiness.material_claims == []
