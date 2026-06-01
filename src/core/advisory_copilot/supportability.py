from __future__ import annotations

from src.core.advisory_copilot.api_models import AdvisoryCopilotSupportabilityResponse
from src.core.advisory_copilot.catalog import list_copilot_action_definitions


def build_advisory_copilot_supportability_response() -> AdvisoryCopilotSupportabilityResponse:
    return AdvisoryCopilotSupportabilityResponse(
        support_status="ADVISE_COPILOT_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED",
        client_ready_publication="BLOCKED",
        supported_action_families=tuple(
            definition.action_family for definition in list_copilot_action_definitions()
        ),
        boundaries=(
            "CLIENT_READY_PUBLICATION is blocked",
            "POLICY_APPROVAL_OR_SIGN_OFF is not delegated to copilot",
            "OMS_ORDER_LIFECYCLE is not delegated to copilot",
            "CLIENT_COMMUNICATION_DELIVERY is not delegated to copilot",
        ),
    )
