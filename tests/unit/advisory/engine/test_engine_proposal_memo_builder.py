from copy import deepcopy
from pathlib import Path

from src.core.proposals.memo_builder import build_advisory_proposal_memo_evidence_pack
from src.core.proposals.memo_models import ProposalMemoMaterialClaim, ProposalMemoSectionKey
from src.core.proposals.memo_policy_enrichment import build_conflict_disclosure_enrichment
from src.core.proposals.memo_section_factory import build_memo_section
from src.core.proposals.memo_source_readiness import build_memo_source_readiness

REPO_ROOT = Path(__file__).resolve().parents[4]


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
        "assumptions_and_limits": {
            "costs_and_fees": {
                "included": False,
                "notes": "Transaction costs and advisory fees are not modeled.",
            },
            "tax": {"included": False, "notes": "Tax impact is not modeled."},
            "execution": {"included": False, "notes": "Execution slippage is not modeled."},
        },
        "disclosures": {
            "risk_disclaimer": "This proposal is based on market-data snapshots.",
            "product_docs": [
                {
                    "instrument_id": "US_EQ_ETF",
                    "doc_ref": "KID/FactSheet reference pending source confirmation",
                }
            ],
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
    assert first.supportability["persistence"] == "SUPPORTED_BY_RFC0024_SLICE6"
    assert first.supportability["api"] == "SUPPORTED_BY_RFC0024_SLICE7"
    assert first.supportability["policy_fee_conflict_enrichment"] == "SUPPORTED_BY_RFC0024_SLICE8"
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
    assert report_readiness.reason_codes == ["MEMO_REPORT_PACKAGE_NOT_REQUESTED"]
    assert "approved advisor-use memo report package" in report_readiness.summary
    assert "later slices" not in report_readiness.summary
    assert report_readiness.material_claims == []


def test_memo_builder_enriches_policy_fee_conflict_sections_without_positive_claims() -> None:
    pack = build_advisory_proposal_memo_evidence_pack(
        proposal_id="pp_memo_policy",
        proposal_version_no=1,
        artifact_json=_artifact(),
        evidence_bundle=_evidence_bundle(),
    )

    suitability = _section(pack, "SUITABILITY_AND_BEST_INTEREST")
    assert suitability.status == "READY"
    assert "Product eligibility and complexity evidence is present" in (
        suitability.material_claims[1].text
    )
    assert "lotus-core:product_eligibility_complexity" in suitability.source_authority_refs

    fees = _section(pack, "FEES_COSTS_TAX_AND_FRICTIONS")
    assert fees.status == "PENDING_REVIEW"
    assert "fee_evidence" in fees.missing_evidence
    assert "tax_evidence" in fees.missing_evidence
    assert "execution_friction_evidence" in fees.missing_evidence
    assert "Transaction costs and advisory fees are not modeled" in fees.summary
    assert fees.material_claims

    conflicts = _section(pack, "CONFLICTS_AND_DISCLOSURES")
    assert conflicts.status == "PENDING_REVIEW"
    assert "conflict_evidence" in conflicts.missing_evidence
    assert "MEMO_CONFLICT_POLICY_EVIDENCE_REVIEW_REQUIRED" in conflicts.reason_codes
    assert "policy packs are implemented" not in conflicts.summary
    assert "active policy evaluation and review evidence" in conflicts.summary
    assert any("Risk disclosure captured" in claim.text for claim in conflicts.material_claims)
    assert any(
        "Product-document references are available" in claim.text
        for claim in conflicts.material_claims
    )
    assert not any(
        "client-ready" in claim.text.lower()
        for section in (suitability, fees, conflicts)
        for claim in section.material_claims
    )


def test_memo_builder_blocks_missing_product_policy_evidence() -> None:
    evidence = deepcopy(_evidence_bundle())
    evidence["inputs"]["shelf_entries"] = []
    evidence["memo_source_readiness"] = build_memo_source_readiness(evidence)
    artifact = deepcopy(_artifact())
    artifact["disclosures"]["product_docs"] = []

    pack = build_advisory_proposal_memo_evidence_pack(
        proposal_id="pp_memo_missing_product_policy",
        proposal_version_no=1,
        artifact_json=artifact,
        evidence_bundle=evidence,
    )

    suitability = _section(pack, "SUITABILITY_AND_BEST_INTEREST")
    assert suitability.status == "BLOCKED"
    assert "shelf_entry:US_EQ_ETF" in suitability.missing_evidence
    assert "PRODUCT_SHELF_ENTRY_MISSING_FOR_PROPOSED_TRADE" in suitability.reason_codes
    assert not any(
        "Product eligibility and complexity evidence is present" in claim.text
        for claim in suitability.material_claims
    )

    conflicts = _section(pack, "CONFLICTS_AND_DISCLOSURES")
    assert conflicts.status == "BLOCKED"
    assert "product_document_evidence" in conflicts.missing_evidence
    assert "PRODUCT_DOCUMENTATION_INCOMPLETE_FOR_PROPOSED_TRADES" in conflicts.reason_codes


def test_conflict_disclosure_enrichment_preserves_missing_doc_and_claim_policy() -> None:
    evidence = deepcopy(_evidence_bundle())
    evidence["inputs"]["proposed_trades"] = [
        {"instrument_id": "US_EQ_ETF", "side": "BUY"},
        {"instrument_id": "SG_STRUCTURED_NOTE", "side": "BUY"},
    ]
    artifact = deepcopy(_artifact())
    artifact["disclosures"]["product_docs"] = [
        {"instrument_id": "US_EQ_ETF", "doc_ref": "Factsheet"}
    ]

    enrichment = build_conflict_disclosure_enrichment(
        artifact=artifact,
        evidence_bundle=evidence,
    )

    assert enrichment.forced_status == "PENDING_REVIEW"
    assert enrichment.forced_missing == ["conflict_evidence", "product_document_evidence"]
    assert enrichment.forced_reasons == [
        "MEMO_CONFLICT_POLICY_EVIDENCE_REVIEW_REQUIRED",
        "PRODUCT_DOCUMENTATION_INCOMPLETE_FOR_PROPOSED_TRADES",
    ]
    assert [claim.claim_id for claim in enrichment.claims] == [
        "conflicts_and_disclosures.claim.1",
        "conflicts_and_disclosures.claim.2",
    ]
    assert "Risk disclosure captured" in enrichment.claims[0].text
    assert "US_EQ_ETF" in enrichment.claims[1].text
    assert "SG_STRUCTURED_NOTE" not in enrichment.claims[1].text


def test_foundational_memo_sections_use_focused_section_builders() -> None:
    groups_source = (REPO_ROOT / "src/core/proposals/memo_section_groups.py").read_text(
        encoding="utf-8"
    )
    foundational_source = (
        REPO_ROOT / "src/core/proposals/memo_foundational_sections.py"
    ).read_text(encoding="utf-8")
    summaries_source = (REPO_ROOT / "src/core/proposals/memo_foundational_summaries.py").read_text(
        encoding="utf-8"
    )

    assert "from src.core.proposals.memo_foundational_sections import" in groups_source
    assert "from src.core.proposals.memo_foundational_summaries import" in foundational_source
    assert "def _build_executive_summary_section(" not in groups_source
    assert "def _build_risk_context_section(" not in groups_source
    assert "def _build_executive_summary_section(" in foundational_source
    assert "def _build_risk_context_section(" in foundational_source
    assert "def decision_summary_text(" not in foundational_source
    assert "def risk_summary(" not in foundational_source
    assert "def decision_summary_text(" in summaries_source
    assert "def risk_summary(" in summaries_source


def test_memo_builder_delegates_section_factory_helpers() -> None:
    builder_source = (REPO_ROOT / "src/core/proposals/memo_builder.py").read_text(encoding="utf-8")
    factory_source = (REPO_ROOT / "src/core/proposals/memo_section_factory.py").read_text(
        encoding="utf-8"
    )

    assert "from src.core.proposals.memo_section_factory import" in builder_source
    assert "build_memo_section" in builder_source
    assert "build_memo_claims" in builder_source
    assert "build_appendix_section" in builder_source
    assert "def _section(" not in builder_source
    assert "def _claims(" not in builder_source
    assert "def build_memo_section(" in factory_source
    assert "def build_memo_claims(" in factory_source
    assert "def build_appendix_section(" in factory_source


def test_memo_section_factory_preserves_blocking_source_evidence_and_hashes() -> None:
    evidence_bundle = {
        "memo_source_readiness": {
            "sections": [
                {
                    "key": "core_product_eligibility_target_market_complexity",
                    "status": "BLOCKED",
                    "missing_evidence": ["target_market"],
                    "reason_codes": ["TARGET_MARKET_MISSING"],
                    "evidence_refs": ["core://target-market"],
                    "owner_service": "lotus-core",
                }
            ]
        }
    }
    claim = ProposalMemoMaterialClaim(
        claim_id="recommendation.claim.1",
        text="Recommendation is source backed.",
        evidence_refs=["proposal://recommendation"],
        source_authority_refs=["lotus-advise:proposal"],
        reason_codes=["RECOMMENDATION_SOURCE_BACKED"],
    )

    section = build_memo_section(
        section_id="RECOMMENDATION",
        title="Recommendation",
        owner_role="ADVISOR",
        audience_visibility=["ADVISOR"],
        source_keys=["core_product_eligibility_target_market_complexity"],
        artifact=_artifact(),
        evidence_bundle=evidence_bundle,
        source_manifest=build_memo_source_readiness(_evidence_bundle()),
        summary="Recommendation summary.",
        claims=[claim],
        forced_status="PENDING_REVIEW",
    )

    assert section.status == "BLOCKED"
    assert section.missing_evidence == ["target_market"]
    assert section.reason_codes == ["TARGET_MARKET_MISSING"]
    assert section.evidence_refs == ["core://target-market", "proposal://recommendation"]
    assert section.source_authority_refs == ["lotus-core", "lotus-advise:proposal"]
    assert section.degraded_evidence == []
    assert section.last_material_input_hash.startswith("sha256:")
    assert section.section_hash.startswith("sha256:")
