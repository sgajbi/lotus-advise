from __future__ import annotations

from src.core.advisory_copilot import (
    WORKFLOW_PACK_CALLER_APP,
    WORKFLOW_PACK_EXECUTION_AUTHORITY,
    business_projection_for_action,
    get_copilot_action_definition,
    guardrail_reason_for_intent,
    is_terminal_review_posture,
    list_copilot_action_definitions,
    required_evidence_sections,
    review_posture_for_action,
    workflow_pack_id_for_action,
)


def test_copilot_catalog_defines_first_wave_actions_without_client_ready_claims() -> None:
    definitions = list_copilot_action_definitions()

    assert {definition.action_family for definition in definitions} == {
        "PROPOSAL_EXPLANATION",
        "EVIDENCE_QA",
        "MEETING_PREPARATION",
        "COMPLIANCE_REVIEW_SUMMARY",
        "OPERATIONS_REPORT_HANDOFF",
        "CLIENT_FOLLOW_UP_DRAFT",
    }

    for definition in definitions:
        assert definition.default_review_posture == "REVIEW_REQUIRED"
        assert definition.client_ready_publication == "BLOCKED"
        assert definition.workflow_pack_id.startswith("advisory_copilot_")
        assert definition.workflow_pack_id.endswith(".pack")
        assert definition.workflow_pack_version == "v1"
        assert definition.workbench_surface_key.startswith("advisory_copilot.")
        assert definition.required_source_dependencies
        assert definition.output_evidence_classes


def test_copilot_catalog_keeps_ai_execution_boundary_in_lotus_ai() -> None:
    definition = get_copilot_action_definition("EVIDENCE_QA")

    assert WORKFLOW_PACK_EXECUTION_AUTHORITY == "lotus-ai"
    assert WORKFLOW_PACK_CALLER_APP == "lotus-advise"
    assert workflow_pack_id_for_action("EVIDENCE_QA") == definition.workflow_pack_id
    assert "RFC0026_ADVISOR_COCKPIT" in definition.required_source_dependencies
    assert required_evidence_sections("EVIDENCE_QA") == (
        "PROPOSAL_CONTEXT",
        "NARRATIVE_POSTURE",
        "MEMO_EVIDENCE",
        "POLICY_POSTURE",
        "COCKPIT_ACTIONS",
    )


def test_copilot_guardrail_foundation_rejects_forbidden_intents_by_stable_reason_code() -> None:
    assert guardrail_reason_for_intent("choose-recommendation") == "AUTONOMOUS_ADVICE_FORBIDDEN"
    assert guardrail_reason_for_intent(" generate trade ") == "TRADE_OR_ORDER_ACTION_FORBIDDEN"
    assert guardrail_reason_for_intent("approve_policy") == "POLICY_APPROVAL_FORBIDDEN"
    assert guardrail_reason_for_intent("publish client ready") == (
        "CLIENT_READY_PUBLICATION_FORBIDDEN"
    )
    assert guardrail_reason_for_intent("override_instructions") == "PROMPT_INJECTION_REJECTED"
    assert guardrail_reason_for_intent("summarize_supported_evidence") is None


def test_copilot_review_foundation_keeps_review_controlled_posture() -> None:
    assert review_posture_for_action("APPROVE_FOR_INTERNAL_USE") == "APPROVED_FOR_INTERNAL_USE"
    assert review_posture_for_action("REJECT") == "REJECTED"
    assert is_terminal_review_posture("REVIEW_REQUIRED") is False
    assert is_terminal_review_posture("APPROVED_FOR_INTERNAL_USE") is True
    assert is_terminal_review_posture("GUARDRAIL_REJECTED") is True


def test_business_projection_uses_clean_private_banking_language() -> None:
    banned_terms = (
        "workflow-pack",
        "provider",
        "prompt",
        "correlation",
        "trace",
        "run ledger",
        "raw payload",
    )

    for definition in list_copilot_action_definitions():
        projection = business_projection_for_action(definition.action_family)
        business_copy = " ".join(
            (projection.label, projection.summary, projection.next_action_label)
        ).lower()

        assert projection.action_family == definition.action_family
        assert projection.label
        assert projection.summary
        assert projection.next_action_label.startswith("Review")
        for banned in banned_terms:
            assert banned not in business_copy
