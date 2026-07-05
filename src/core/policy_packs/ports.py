from __future__ import annotations

from typing import Any, Protocol

from src.core.policy_packs.ai_models import PolicyAiEvidenceDraft
from src.core.proposals.response_models import ProposalReportResponse


class PolicyReportPackageClient(Protocol):
    def request_policy_sign_off_report_package(
        self,
        *,
        request: dict[str, Any],
    ) -> ProposalReportResponse: ...


class PolicyAiEvidenceClient(Protocol):
    def generate_policy_evidence_summary(
        self,
        *,
        policy_evidence: dict[str, Any],
        requested_actions: list[str],
        requested_by: str,
        reason: dict[str, Any],
    ) -> PolicyAiEvidenceDraft: ...
