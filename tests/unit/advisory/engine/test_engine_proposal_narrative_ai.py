from __future__ import annotations

from typing import cast

from src.core.advisory.narrative_ai import apply_ai_draft_sections
from src.core.advisory.narrative_ai_models import ProposalNarrativeAiLineage
from src.core.advisory.narrative_ai_ports import (
    ProposalNarrativeDraftResponse,
    ProposalNarrativeDraftSection,
)
from src.core.advisory.narrative_ai_ports import (
    ProposalNarrativeDraftUnavailableError as LotusAIProposalNarrativeUnavailableError,
)
from src.core.advisory.narrative_grounding_models import (
    ProposalNarrativeGroundingPacket,
    ProposalNarrativeSourceRef,
)
from src.core.advisory.narrative_policy_models import (
    ProposalNarrativePolicy,
    ProposalNarrativePolicyContext,
)
from src.core.advisory.narrative_request_models import ProposalNarrativeRequest
from src.core.advisory.narrative_section_models import ProposalNarrativeSection
from src.core.advisory.narrative_types import ProposalNarrativeSectionKey


def test_apply_ai_draft_sections_preserves_deterministic_grounding_metadata() -> None:
    source_ref = ProposalNarrativeSourceRef(
        ref_type="decision_summary",
        ref_id="proposal_result_001",
        field_path="decision_status",
    )
    deterministic_sections = [
        ProposalNarrativeSection(
            section_key="EXECUTIVE_SUMMARY",
            title="Executive Summary",
            text="Deterministic text.",
            source_refs=[source_ref],
            limitation_refs=["risk_lens"],
        )
    ]

    sections, lineage, generation_mode = apply_ai_draft_sections(
        packet=_packet(),
        narrative_policy=_policy(),
        request=ProposalNarrativeRequest(requested_by="advisor_123"),
        deterministic_sections=deterministic_sections,
        requested_sections=["EXECUTIVE_SUMMARY"],
        generate_ai_draft=lambda **_: ProposalNarrativeDraftResponse(
            sections=(
                ProposalNarrativeDraftSection(
                    section_key="EXECUTIVE_SUMMARY",
                    title="AI Executive Summary",
                    text="AI-assisted text.",
                ),
                ProposalNarrativeDraftSection(
                    section_key=cast(ProposalNarrativeSectionKey, "UNKNOWN_SECTION"),
                    title="Unsupported",
                    text="This section is not grounded.",
                ),
            ),
            lineage=_lineage(),
        ),
    )

    assert generation_mode == "AI_ASSISTED_DRAFT"
    assert lineage.fallback_reason is None
    assert [section.section_key for section in sections] == ["EXECUTIVE_SUMMARY"]
    assert sections[0].title == "AI Executive Summary"
    assert sections[0].text == "AI-assisted text."
    assert sections[0].source_refs == [source_ref]
    assert sections[0].limitation_refs == ["risk_lens"]


def test_apply_ai_draft_sections_falls_back_with_adapter_reason() -> None:
    deterministic_sections = [_section()]

    sections, lineage, generation_mode = apply_ai_draft_sections(
        packet=_packet(),
        narrative_policy=_policy(),
        request=ProposalNarrativeRequest(),
        deterministic_sections=deterministic_sections,
        requested_sections=["EXECUTIVE_SUMMARY"],
        generate_ai_draft=_raise_custom_ai_unavailable,
    )

    assert sections == deterministic_sections
    assert generation_mode == "DETERMINISTIC_TEMPLATE"
    assert lineage.fallback_reason == "LOTUS_AI_RATE_LIMITED"
    assert lineage.workflow_run_id is None


def test_apply_ai_draft_sections_falls_back_when_no_draft_sections_are_grounded() -> None:
    deterministic_sections = [_section()]

    sections, lineage, generation_mode = apply_ai_draft_sections(
        packet=_packet(),
        narrative_policy=_policy(),
        request=ProposalNarrativeRequest(),
        deterministic_sections=deterministic_sections,
        requested_sections=["EXECUTIVE_SUMMARY"],
        generate_ai_draft=lambda **_: ProposalNarrativeDraftResponse(
            sections=(
                ProposalNarrativeDraftSection(
                    section_key=cast(ProposalNarrativeSectionKey, "UNKNOWN_SECTION"),
                    title="Unsupported",
                    text="This section is not grounded.",
                ),
            ),
            lineage=_lineage(),
        ),
    )

    assert sections == deterministic_sections
    assert generation_mode == "DETERMINISTIC_TEMPLATE"
    assert lineage.fallback_reason == "LOTUS_AI_NARRATIVE_UNAVAILABLE"
    assert lineage.workflow_run_id is None


def _raise_custom_ai_unavailable(**_: object) -> ProposalNarrativeDraftResponse:
    raise LotusAIProposalNarrativeUnavailableError("LOTUS_AI_RATE_LIMITED")


def _section() -> ProposalNarrativeSection:
    return ProposalNarrativeSection(
        section_key="EXECUTIVE_SUMMARY",
        title="Executive Summary",
        text="Deterministic text.",
    )


def _packet() -> ProposalNarrativeGroundingPacket:
    return ProposalNarrativeGroundingPacket(
        packet_id="pgp_test",
        policy_version="proposal-narrative-deterministic.v1",
        audience="ADVISOR_REVIEW",
    )


def _policy() -> ProposalNarrativePolicy:
    return ProposalNarrativePolicy(
        policy_version="advisory-narrative-policy.2026-05",
        status="READY_FOR_ADVISOR_REVIEW",
        context=ProposalNarrativePolicyContext(
            jurisdiction="SG",
            product_types=["EQUITY"],
            risk_posture="STANDARD",
            client_audience="ADVISOR_REVIEW",
        ),
    )


def _lineage() -> ProposalNarrativeAiLineage:
    return ProposalNarrativeAiLineage(
        requested_generation_mode="AI_ASSISTED_DRAFT",
        adapter_version="proposal-narrative-lotus-ai-adapter.v1",
        workflow_pack_id="proposal_narrative_draft.pack",
        workflow_pack_version="v1",
        prompt_template_version="proposal-narrative-instructions.v1",
        model_version="lotus-ai-governed-model.v1",
        workflow_run_id="packrun_proposal_narrative_001",
    )
