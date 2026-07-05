from __future__ import annotations

from typing import Any

from src.core.policy_packs.ai_models import PolicyAiEvidenceDraft
from src.core.policy_packs.ports import PolicyAiEvidenceClient, PolicyReportPackageClient
from src.core.proposals.response_models import ProposalReportResponse
from src.integrations.lotus_ai.policy_evidence import generate_policy_evidence_summary_with_lotus_ai
from src.integrations.lotus_report import request_policy_sign_off_report_package_with_lotus_report


class LotusReportPolicyReportPackageClient:
    def request_policy_sign_off_report_package(
        self,
        *,
        request: dict[str, Any],
    ) -> ProposalReportResponse:
        return request_policy_sign_off_report_package_with_lotus_report(request=request)


class LotusAiPolicyEvidenceClient:
    def generate_policy_evidence_summary(
        self,
        *,
        policy_evidence: dict[str, Any],
        requested_actions: list[str],
        requested_by: str,
        reason: dict[str, Any],
    ) -> PolicyAiEvidenceDraft:
        return generate_policy_evidence_summary_with_lotus_ai(
            policy_evidence=policy_evidence,
            requested_actions=requested_actions,
            requested_by=requested_by,
            reason=reason,
        )


_REPORT_PACKAGE_CLIENT: PolicyReportPackageClient = LotusReportPolicyReportPackageClient()
_AI_EVIDENCE_CLIENT: PolicyAiEvidenceClient = LotusAiPolicyEvidenceClient()


def get_policy_report_package_client() -> PolicyReportPackageClient:
    return _REPORT_PACKAGE_CLIENT


def get_policy_ai_evidence_client() -> PolicyAiEvidenceClient:
    return _AI_EVIDENCE_CLIENT


def set_policy_report_package_client_for_tests(
    client: PolicyReportPackageClient | None,
) -> None:
    global _REPORT_PACKAGE_CLIENT
    _REPORT_PACKAGE_CLIENT = client or LotusReportPolicyReportPackageClient()


def set_policy_ai_evidence_client_for_tests(client: PolicyAiEvidenceClient | None) -> None:
    global _AI_EVIDENCE_CLIENT
    _AI_EVIDENCE_CLIENT = client or LotusAiPolicyEvidenceClient()
