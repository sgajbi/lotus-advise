from src.core.advisory.narrative_models import ProposalNarrativeSection, ProposalNarrativeSourceRef
from src.core.advisory.narrative_policy import evaluate_proposal_narrative_guardrails


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
