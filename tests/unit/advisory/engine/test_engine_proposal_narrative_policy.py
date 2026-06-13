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
