from __future__ import annotations

from importlib import import_module
from typing import Final

_EXPORTS: Final[dict[str, tuple[str, str]]] = {
    "AdvisoryCopilotAiDraft": (
        "src.integrations.lotus_ai.advisory_copilot",
        "AdvisoryCopilotAiDraft",
    ),
    "LotusAIProposalMemoUnavailableError": (
        "src.integrations.lotus_ai.proposal_memo",
        "LotusAIProposalMemoUnavailableError",
    ),
    "LotusAIProposalNarrativeUnavailableError": (
        "src.integrations.lotus_ai.proposal_narrative",
        "LotusAIProposalNarrativeUnavailableError",
    ),
    "LotusAIPolicyEvidenceUnavailableError": (
        "src.integrations.lotus_ai.policy_evidence",
        "LotusAIPolicyEvidenceUnavailableError",
    ),
    "LotusAIRationaleUnavailableError": (
        "src.integrations.lotus_ai.rationale",
        "LotusAIRationaleUnavailableError",
    ),
    "apply_workspace_rationale_review_action_with_lotus_ai": (
        "src.integrations.lotus_ai.rationale",
        "apply_workspace_rationale_review_action_with_lotus_ai",
    ),
    "build_advisory_copilot_unavailable_draft": (
        "src.integrations.lotus_ai.advisory_copilot",
        "build_advisory_copilot_unavailable_draft",
    ),
    "build_ai_fallback_lineage": (
        "src.integrations.lotus_ai.proposal_narrative",
        "build_ai_fallback_lineage",
    ),
    "build_lotus_ai_dependency_state": (
        "src.integrations.lotus_ai.adapter",
        "build_lotus_ai_dependency_state",
    ),
    "build_policy_ai_unavailable_evidence": (
        "src.integrations.lotus_ai.policy_evidence",
        "build_policy_ai_unavailable_evidence",
    ),
    "build_proposal_memo_ai_unavailable_commentary": (
        "src.integrations.lotus_ai.proposal_memo",
        "build_proposal_memo_ai_unavailable_commentary",
    ),
    "generate_advisory_copilot_draft_with_lotus_ai": (
        "src.integrations.lotus_ai.advisory_copilot",
        "generate_advisory_copilot_draft_with_lotus_ai",
    ),
    "generate_policy_evidence_summary_with_lotus_ai": (
        "src.integrations.lotus_ai.policy_evidence",
        "generate_policy_evidence_summary_with_lotus_ai",
    ),
    "generate_proposal_memo_commentary_with_lotus_ai": (
        "src.integrations.lotus_ai.proposal_memo",
        "generate_proposal_memo_commentary_with_lotus_ai",
    ),
    "generate_proposal_narrative_draft_with_lotus_ai": (
        "src.integrations.lotus_ai.proposal_narrative",
        "generate_proposal_narrative_draft_with_lotus_ai",
    ),
    "generate_workspace_rationale_with_lotus_ai": (
        "src.integrations.lotus_ai.rationale",
        "generate_workspace_rationale_with_lotus_ai",
    ),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> object:
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
