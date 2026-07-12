from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from src.core.advisory_copilot.catalog import list_copilot_action_definitions
from src.core.advisory_copilot.type_models import CopilotActionFamily

ADVISORY_COPILOT_APPROVED_PROVIDER_ID = "lotus-ai"
ADVISORY_COPILOT_APPROVED_MODEL_VERSION = "lotus-ai-governed-model.v1"
ADVISORY_COPILOT_RETIRED_MODEL_VERSION = "lotus-ai-experimental-model.v2"
ADVISORY_COPILOT_APPROVED_INSTRUCTION_SET = "advisory-copilot-instructions.v1"
ADVISORY_COPILOT_PROMPT_TEMPLATE_VERSION = "advisory-copilot-prompt-template.v1"
ADVISORY_COPILOT_OUTPUT_SCHEMA_VERSION = "advisory-copilot-output-schema.v1"
ADVISORY_COPILOT_EVALUATION_PACK_REF = "advisory-copilot-eval-pack.v1"

ModelApprovalStatus = Literal["APPROVED", "RETIRED"]
ModelApprovalDecisionCode = Literal[
    "APPROVED",
    "COPILOT_MODEL_APPROVAL_NOT_FOUND",
    "COPILOT_MODEL_ENVIRONMENT_NOT_APPROVED",
    "COPILOT_MODEL_IDENTITY_MISSING",
    "COPILOT_MODEL_IDENTITY_MISMATCH",
    "COPILOT_MODEL_RETIRED",
]

_APPROVED_ENVIRONMENTS = (
    "DEVELOPMENT",
    "LOCAL",
    "DEV",
    "TEST",
    "CI",
    "UAT",
    "STAGING",
    "PRODUCTION",
)


@dataclass(frozen=True)
class AdvisoryCopilotModelApproval:
    inventory_id: str
    action_family: CopilotActionFamily
    provider_id: str
    model_version: str
    status: ModelApprovalStatus
    workflow_pack_id: str
    workflow_pack_version: str
    approved_instruction_set: str
    prompt_template_version: str
    output_schema_version: str
    evaluation_pack_ref: str
    approved_environments: tuple[str, ...]
    risk_tier: str
    owner: str
    data_class: str
    approval_reference: str
    evaluation_result_ref: str
    release_evidence_ref: str
    change_reference: str
    rollback_reference: str | None = None
    retirement_reference: str | None = None

    def lineage(self, *, environment: str) -> dict[str, str | None]:
        return {
            "model_inventory_id": self.inventory_id,
            "approved_model_provider_id": self.provider_id,
            "approved_model_version": self.model_version,
            "model_approval_status": self.status,
            "model_approval_environment": normalize_model_environment(environment),
            "model_risk_tier": self.risk_tier,
            "model_owner": self.owner,
            "model_data_class": self.data_class,
            "model_approval_reference": self.approval_reference,
            "model_evaluation_result_ref": self.evaluation_result_ref,
            "model_release_evidence_ref": self.release_evidence_ref,
            "model_change_reference": self.change_reference,
            "model_rollback_reference": self.rollback_reference,
            "model_retirement_reference": self.retirement_reference,
        }


@dataclass(frozen=True)
class AdvisoryCopilotModelApprovalDecision:
    approved: bool
    code: ModelApprovalDecisionCode
    approval: AdvisoryCopilotModelApproval | None = None


def list_advisory_copilot_model_approvals() -> tuple[AdvisoryCopilotModelApproval, ...]:
    return (*_active_model_approvals(), *_retired_model_approvals())


def advisory_copilot_model_approval_for_request(
    *,
    action_family: CopilotActionFamily,
    environment: str,
    workflow_pack_id: str,
    workflow_pack_version: str,
    approved_instruction_set: str,
    prompt_template_version: str,
    output_schema_version: str,
    evaluation_pack_ref: str,
) -> AdvisoryCopilotModelApprovalDecision:
    approvals = _active_request_approvals(
        action_family=action_family,
        workflow_pack_id=workflow_pack_id,
        workflow_pack_version=workflow_pack_version,
        approved_instruction_set=approved_instruction_set,
        prompt_template_version=prompt_template_version,
        output_schema_version=output_schema_version,
        evaluation_pack_ref=evaluation_pack_ref,
    )
    if not approvals:
        return AdvisoryCopilotModelApprovalDecision(
            approved=False,
            code="COPILOT_MODEL_APPROVAL_NOT_FOUND",
        )
    return _environment_approval_decision(approvals=approvals, environment=environment)


def validate_advisory_copilot_model_response(
    *,
    expected_approval: AdvisoryCopilotModelApproval,
    provider_id: str | None,
    model_version: str | None,
) -> AdvisoryCopilotModelApprovalDecision:
    if not provider_id or not model_version:
        return AdvisoryCopilotModelApprovalDecision(
            approved=False,
            code="COPILOT_MODEL_IDENTITY_MISSING",
            approval=expected_approval,
        )
    if (
        provider_id != expected_approval.provider_id
        or model_version != expected_approval.model_version
    ):
        if _is_retired_model(provider_id=provider_id, model_version=model_version):
            return AdvisoryCopilotModelApprovalDecision(
                approved=False,
                code="COPILOT_MODEL_RETIRED",
                approval=expected_approval,
            )
        return AdvisoryCopilotModelApprovalDecision(
            approved=False,
            code="COPILOT_MODEL_IDENTITY_MISMATCH",
            approval=expected_approval,
        )
    return AdvisoryCopilotModelApprovalDecision(
        approved=True,
        code="APPROVED",
        approval=expected_approval,
    )


def normalize_model_environment(value: str) -> str:
    return " ".join(value.split()).upper() or "DEVELOPMENT"


def _active_request_approvals(
    *,
    action_family: CopilotActionFamily,
    workflow_pack_id: str,
    workflow_pack_version: str,
    approved_instruction_set: str,
    prompt_template_version: str,
    output_schema_version: str,
    evaluation_pack_ref: str,
) -> tuple[AdvisoryCopilotModelApproval, ...]:
    return tuple(
        approval
        for approval in list_advisory_copilot_model_approvals()
        if approval.status == "APPROVED"
        and _approval_matches_request(
            approval=approval,
            action_family=action_family,
            workflow_pack_id=workflow_pack_id,
            workflow_pack_version=workflow_pack_version,
            approved_instruction_set=approved_instruction_set,
            prompt_template_version=prompt_template_version,
            output_schema_version=output_schema_version,
            evaluation_pack_ref=evaluation_pack_ref,
        )
    )


def _approval_matches_request(
    *,
    approval: AdvisoryCopilotModelApproval,
    action_family: CopilotActionFamily,
    workflow_pack_id: str,
    workflow_pack_version: str,
    approved_instruction_set: str,
    prompt_template_version: str,
    output_schema_version: str,
    evaluation_pack_ref: str,
) -> bool:
    return (
        approval.action_family == action_family
        and approval.workflow_pack_id == workflow_pack_id
        and approval.workflow_pack_version == workflow_pack_version
        and approval.approved_instruction_set == approved_instruction_set
        and approval.prompt_template_version == prompt_template_version
        and approval.output_schema_version == output_schema_version
        and approval.evaluation_pack_ref == evaluation_pack_ref
    )


def _environment_approval_decision(
    *,
    approvals: tuple[AdvisoryCopilotModelApproval, ...],
    environment: str,
) -> AdvisoryCopilotModelApprovalDecision:
    normalized_environment = normalize_model_environment(environment)
    for approval in approvals:
        if normalized_environment in approval.approved_environments:
            return AdvisoryCopilotModelApprovalDecision(
                approved=True,
                code="APPROVED",
                approval=approval,
            )
    return AdvisoryCopilotModelApprovalDecision(
        approved=False,
        code="COPILOT_MODEL_ENVIRONMENT_NOT_APPROVED",
    )


def _active_model_approvals() -> tuple[AdvisoryCopilotModelApproval, ...]:
    return tuple(
        AdvisoryCopilotModelApproval(
            inventory_id=f"advisory-copilot.{definition.action_family.lower()}.lotus-ai.v1",
            action_family=definition.action_family,
            provider_id=ADVISORY_COPILOT_APPROVED_PROVIDER_ID,
            model_version=ADVISORY_COPILOT_APPROVED_MODEL_VERSION,
            status="APPROVED",
            workflow_pack_id=definition.workflow_pack_id,
            workflow_pack_version=definition.workflow_pack_version,
            approved_instruction_set=ADVISORY_COPILOT_APPROVED_INSTRUCTION_SET,
            prompt_template_version=ADVISORY_COPILOT_PROMPT_TEMPLATE_VERSION,
            output_schema_version=ADVISORY_COPILOT_OUTPUT_SCHEMA_VERSION,
            evaluation_pack_ref=ADVISORY_COPILOT_EVALUATION_PACK_REF,
            approved_environments=_APPROVED_ENVIRONMENTS,
            risk_tier="MODEL_RISK_TIER_2_ADVISOR_ASSISTIVE",
            owner="lotus-ai-model-risk",
            data_class="ADVISORY_REVIEW_EVIDENCE",
            approval_reference="MODEL-RISK-APPROVAL-ADVISORY-COPILOT-V1",
            evaluation_result_ref="advisory-copilot-eval-pack.v1:pass",
            release_evidence_ref="lotus-ai-release:advisory-copilot-workflow-packs:v1",
            change_reference="change:advisory-copilot-model-governance:v1",
            rollback_reference="rollback:advisory-copilot-model-governance:v2-to-v1",
        )
        for definition in list_copilot_action_definitions()
    )


def _retired_model_approvals() -> tuple[AdvisoryCopilotModelApproval, ...]:
    return tuple(
        replace(
            approval,
            inventory_id=approval.inventory_id.replace(".v1", ".retired-v2"),
            model_version=ADVISORY_COPILOT_RETIRED_MODEL_VERSION,
            status="RETIRED",
            approval_reference="MODEL-RISK-APPROVAL-ADVISORY-COPILOT-V2-RETIRED",
            evaluation_result_ref="advisory-copilot-eval-pack.v2:failed",
            release_evidence_ref="lotus-ai-release:advisory-copilot-workflow-packs:v2",
            change_reference="change:advisory-copilot-model-governance:v2-retired",
            rollback_reference=None,
            retirement_reference="retirement:advisory-copilot-model-governance:v2",
        )
        for approval in _active_model_approvals()
    )


def _is_retired_model(*, provider_id: str, model_version: str) -> bool:
    return any(
        approval.provider_id == provider_id
        and approval.model_version == model_version
        and approval.status == "RETIRED"
        for approval in _retired_model_approvals()
    )
