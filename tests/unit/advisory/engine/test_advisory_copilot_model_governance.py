from __future__ import annotations

import json
from pathlib import Path

from src.core.advisory_copilot.catalog import list_copilot_action_definitions
from src.core.advisory_copilot.model_governance import (
    ADVISORY_COPILOT_APPROVED_MODEL_VERSION,
    ADVISORY_COPILOT_APPROVED_PROVIDER_ID,
    ADVISORY_COPILOT_RETIRED_MODEL_VERSION,
    AdvisoryCopilotModelApproval,
    AdvisoryCopilotModelApprovalDecision,
    advisory_copilot_model_approval_for_request,
    list_advisory_copilot_model_approvals,
    validate_advisory_copilot_model_response,
)

MODEL_INVENTORY_CONTRACT_PATH = Path("contracts/advisory-copilot/approved-model-inventory.v1.json")


def test_advisory_copilot_model_inventory_covers_each_workflow_pack() -> None:
    action_definitions = list_copilot_action_definitions()
    approvals = list_advisory_copilot_model_approvals()
    active_approvals = tuple(approval for approval in approvals if approval.status == "APPROVED")

    assert len(active_approvals) == len(action_definitions)
    assert {approval.action_family for approval in active_approvals} == {
        definition.action_family for definition in action_definitions
    }
    for approval in active_approvals:
        assert approval.provider_id == ADVISORY_COPILOT_APPROVED_PROVIDER_ID
        assert approval.model_version == ADVISORY_COPILOT_APPROVED_MODEL_VERSION
        assert approval.owner == "lotus-ai-model-risk"
        assert approval.risk_tier == "MODEL_RISK_TIER_2_ADVISOR_ASSISTIVE"
        assert approval.approval_reference
        assert approval.evaluation_result_ref.endswith(":pass")
        assert approval.release_evidence_ref
        assert approval.change_reference


def test_advisory_copilot_model_inventory_contract_matches_runtime_registry() -> None:
    contract = json.loads(MODEL_INVENTORY_CONTRACT_PATH.read_text(encoding="utf-8"))
    active_approvals = tuple(
        approval
        for approval in list_advisory_copilot_model_approvals()
        if approval.status == "APPROVED"
    )
    approved_combinations = {
        (
            item["action_family"],
            item["workflow_pack_id"],
            item["workflow_pack_version"],
        )
        for item in contract["approved_workflow_pack_combinations"]
    }

    assert contract["schema_version"] == (
        "lotus.advise.advisory-copilot-approved-model-inventory.v1"
    )
    assert contract["fail_closed"] is True
    assert contract["approved_provider_id"] == ADVISORY_COPILOT_APPROVED_PROVIDER_ID
    assert contract["active_model_version"] == ADVISORY_COPILOT_APPROVED_MODEL_VERSION
    assert ADVISORY_COPILOT_RETIRED_MODEL_VERSION in contract["retired_model_versions"]
    assert approved_combinations == {
        (
            approval.action_family,
            approval.workflow_pack_id,
            approval.workflow_pack_version,
        )
        for approval in active_approvals
    }
    assert contract["model_governance"]["approval_reference"] == (
        "MODEL-RISK-APPROVAL-ADVISORY-COPILOT-V1"
    )
    assert contract["model_risk_controls"]["evaluation_pack_ref"] == (
        "advisory-copilot-eval-pack.v1"
    )


def test_advisory_copilot_model_request_allows_governed_environment() -> None:
    approval = _approved_request()

    assert approval.approved is True
    assert approval.code == "APPROVED"
    assert approval.approval is not None
    assert approval.approval.rollback_reference == (
        "rollback:advisory-copilot-model-governance:v2-to-v1"
    )


def test_advisory_copilot_model_request_rejects_unapproved_environment() -> None:
    decision = advisory_copilot_model_approval_for_request(
        action_family="PROPOSAL_EXPLANATION",
        environment="EXPERIMENTAL_LAB",
        workflow_pack_id="advisory_copilot_proposal_explanation.pack",
        workflow_pack_version="v1",
        approved_instruction_set="advisory-copilot-instructions.v1",
        prompt_template_version="advisory-copilot-prompt-template.v1",
        output_schema_version="advisory-copilot-output-schema.v1",
        evaluation_pack_ref="advisory-copilot-eval-pack.v1",
    )

    assert decision.approved is False
    assert decision.code == "COPILOT_MODEL_ENVIRONMENT_NOT_APPROVED"


def test_advisory_copilot_model_response_allows_approved_identity() -> None:
    approval = _approval()

    decision = validate_advisory_copilot_model_response(
        expected_approval=approval,
        provider_id=ADVISORY_COPILOT_APPROVED_PROVIDER_ID,
        model_version=ADVISORY_COPILOT_APPROVED_MODEL_VERSION,
    )

    assert decision.approved is True
    assert decision.approval == approval


def test_advisory_copilot_model_response_rejects_missing_identity() -> None:
    decision = validate_advisory_copilot_model_response(
        expected_approval=_approval(),
        provider_id=None,
        model_version=None,
    )

    assert decision.approved is False
    assert decision.code == "COPILOT_MODEL_IDENTITY_MISSING"


def test_advisory_copilot_model_response_rejects_unknown_or_mismatched_identity() -> None:
    decision = validate_advisory_copilot_model_response(
        expected_approval=_approval(),
        provider_id="unapproved-provider",
        model_version="unapproved-model.v1",
    )

    assert decision.approved is False
    assert decision.code == "COPILOT_MODEL_IDENTITY_MISMATCH"


def test_advisory_copilot_model_response_rejects_retired_model_after_rollback() -> None:
    decision = validate_advisory_copilot_model_response(
        expected_approval=_approval(),
        provider_id=ADVISORY_COPILOT_APPROVED_PROVIDER_ID,
        model_version=ADVISORY_COPILOT_RETIRED_MODEL_VERSION,
    )

    assert decision.approved is False
    assert decision.code == "COPILOT_MODEL_RETIRED"


def _approved_request() -> AdvisoryCopilotModelApprovalDecision:
    return advisory_copilot_model_approval_for_request(
        action_family="PROPOSAL_EXPLANATION",
        environment="DEVELOPMENT",
        workflow_pack_id="advisory_copilot_proposal_explanation.pack",
        workflow_pack_version="v1",
        approved_instruction_set="advisory-copilot-instructions.v1",
        prompt_template_version="advisory-copilot-prompt-template.v1",
        output_schema_version="advisory-copilot-output-schema.v1",
        evaluation_pack_ref="advisory-copilot-eval-pack.v1",
    )


def _approval() -> AdvisoryCopilotModelApproval:
    decision = _approved_request()
    assert decision.approval is not None
    return decision.approval
