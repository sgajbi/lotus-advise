from src.core.advisory.artifact_evidence_models import (
    ProposalArtifactEvidenceBundle,
    ProposalArtifactEvidenceInputs,
)
from src.core.advisory.artifact_models import ProposalArtifact
from src.core.advisory.artifact_trade_models import (
    ProposalArtifactFx,
    ProposalArtifactTradesAndFunding,
)
from src.core.advisory.narrative_grounding_models import ProposalNarrativeSourceRef
from src.core.advisory.narrative_policy import (
    evaluate_proposal_narrative_guardrails,
    resolve_narrative_product_types,
    resolve_proposal_narrative_policy,
)
from src.core.advisory.narrative_request_models import ProposalNarrativeRequest
from src.core.advisory.narrative_section_models import ProposalNarrativeSection


def _source_ref() -> ProposalNarrativeSourceRef:
    return ProposalNarrativeSourceRef(
        ref_type="proposal_artifact",
        ref_id="pa_guardrail",
        field_path="summary",
    )


def test_narrative_guardrails_reject_unsupported_claims() -> None:
    section = ProposalNarrativeSection(
        section_key="EXECUTIVE_SUMMARY",
        title="Executive Summary",
        text="This proposal provides a guaranteed return for the client.",
        source_refs=[_source_ref()],
    )

    results = evaluate_proposal_narrative_guardrails([section])

    assert results[0].status == "FAIL"
    assert results[0].guardrail_id == "GR_UNSUPPORTED_GUARANTEED_RETURN"
    assert results[0].section_key == "EXECUTIVE_SUMMARY"


def test_narrative_guardrails_reject_ungrounded_sections() -> None:
    section = ProposalNarrativeSection(
        section_key="RECOMMENDATION_RATIONALE",
        title="Recommendation Rationale",
        text="The recommendation is based on proposal evidence.",
        source_refs=[],
    )

    results = evaluate_proposal_narrative_guardrails([section])

    assert results[0].status == "FAIL"
    assert results[0].guardrail_id == "GR_MISSING_SOURCE_REF"


def test_narrative_guardrails_return_pass_when_claims_are_supported_and_grounded() -> None:
    section = ProposalNarrativeSection(
        section_key="RISK_AND_CONCENTRATION",
        title="Risk Review",
        text="The proposal remains subject to advisory review and market risk.",
        source_refs=[_source_ref()],
    )

    results = evaluate_proposal_narrative_guardrails([section])

    assert len(results) == 1
    assert results[0].status == "PASS"
    assert results[0].guardrail_id == "GR_UNSUPPORTED_CLAIMS"


def test_narrative_product_types_merge_request_and_source_evidence() -> None:
    artifact = ProposalArtifact.model_construct(
        evidence_bundle=ProposalArtifactEvidenceBundle.model_construct(
            inputs=ProposalArtifactEvidenceInputs.model_construct(
                portfolio_snapshot={},
                market_data_snapshot={},
                shelf_entries=[
                    "bad-shelf-entry",
                    {
                        "asset_class": "Equity",
                        "attributes": {"product_type": "structured_note"},
                    },
                    {"asset_class": "Cash", "attributes": {"product_type": None}},
                    {"asset_class": "Unknown", "attributes": "bad-attributes"},
                ],
                options={},
                proposed_cash_flows=[],
                proposed_trades=[],
            )
        ),
        trades_and_funding=ProposalArtifactTradesAndFunding(
            fx_list=[
                ProposalArtifactFx(
                    intent_id="fx_1",
                    pair="USD/SGD",
                    buy_amount="100.00",
                    sell_amount_estimated="135.00",
                )
            ],
            ordering_policy="FX->BUY",
        ),
    )
    request = ProposalNarrativeRequest(product_types=[" fixed income "])

    assert resolve_narrative_product_types(artifact=artifact, request=request) == [
        "CASH",
        "EQUITY",
        "FIXED_INCOME",
        "FX",
        "STRUCTURED_NOTE",
    ]


def test_narrative_policy_selects_supported_disclosures_from_evidence_and_risk() -> None:
    artifact = ProposalArtifact.model_construct(
        evidence_bundle=ProposalArtifactEvidenceBundle.model_construct(
            inputs=ProposalArtifactEvidenceInputs.model_construct(
                portfolio_snapshot={},
                market_data_snapshot={},
                shelf_entries=[{"asset_class": "Equities", "attributes": {}}],
                options={},
                proposed_cash_flows=[],
                proposed_trades=[],
            )
        ),
        trades_and_funding=ProposalArtifactTradesAndFunding(fx_list=[], ordering_policy="BUY"),
        risk_lens=type(
            "RiskLens",
            (),
            {
                "status": "AVAILABLE",
                "summary": "issuer concentration increases",
                "highlights": [],
            },
        )(),
        suitability_summary=type(
            "SuitabilitySummary",
            (),
            {"highest_severity_new": "LOW"},
        )(),
    )

    policy = resolve_proposal_narrative_policy(
        artifact=artifact,
        request=ProposalNarrativeRequest(jurisdiction="sg"),
    )

    disclosure_ids = {item.disclosure_id for item in policy.required_disclosures}
    assert policy.status == "READY_FOR_ADVISOR_REVIEW"
    assert policy.context.product_types == ["EQUITY"]
    assert policy.context.risk_posture == "CONCENTRATION_REVIEW"
    assert disclosure_ids == {
        "DISC_SG_GENERAL_MARKET_RISK",
        "DISC_SG_EQUITY_PRODUCT_RISK",
        "DISC_SG_CONCENTRATION_REVIEW",
    }


def test_narrative_policy_blocks_client_ready_when_disclosure_policy_is_missing() -> None:
    artifact = ProposalArtifact.model_construct(
        evidence_bundle=ProposalArtifactEvidenceBundle.model_construct(
            inputs=ProposalArtifactEvidenceInputs.model_construct(
                portfolio_snapshot={},
                market_data_snapshot={},
                shelf_entries=[],
                options={},
                proposed_cash_flows=[],
                proposed_trades=[],
            )
        ),
        trades_and_funding=ProposalArtifactTradesAndFunding(fx_list=[], ordering_policy="BUY"),
        risk_lens=type(
            "RiskLens",
            (),
            {"status": "UNAVAILABLE", "summary": "", "highlights": []},
        )(),
        suitability_summary=type(
            "SuitabilitySummary",
            (),
            {"highest_severity_new": "LOW"},
        )(),
    )

    policy = resolve_proposal_narrative_policy(
        artifact=artifact,
        request=ProposalNarrativeRequest(
            jurisdiction="hk",
            client_audience="CLIENT_READY",
        ),
    )

    assert policy.status == "BLOCKED_CLIENT_READY"
    assert policy.required_disclosures == []
    assert policy.client_ready_blockers == [
        "CLIENT_READY_DISCLOSURE_POLICY_UNAVAILABLE",
        "CLIENT_READY_DISCLOSURES_NOT_SELECTED",
        "CLIENT_READY_NARRATIVE_RELEASE_NOT_SUPPORTED",
    ]
