import sys
from typing import Any, cast

from src.core.proposals.models import ProposalReportResponse
from src.integrations.base import IntegrationDependencyState, build_dependency_state


class LotusReportUnavailableError(Exception):
    pass


def build_lotus_report_dependency_state() -> IntegrationDependencyState:
    return build_dependency_state(
        key="lotus_report",
        service_name="lotus-report",
        description="Lotus-branded reporting and portfolio review payload service.",
        base_url_env="LOTUS_REPORT_BASE_URL",
    )


def request_proposal_report_with_lotus_report(*, request: dict[str, Any]) -> ProposalReportResponse:
    main_module = sys.modules.get("src.api.main")
    if main_module is None:
        raise LotusReportUnavailableError("LOTUS_REPORT_REQUEST_UNAVAILABLE")

    override = getattr(main_module, "request_proposal_report_with_lotus_report", None)
    if override is None:
        raise LotusReportUnavailableError("LOTUS_REPORT_REQUEST_UNAVAILABLE")

    response = override(request=request)
    return cast(ProposalReportResponse, ProposalReportResponse.model_validate(response))
