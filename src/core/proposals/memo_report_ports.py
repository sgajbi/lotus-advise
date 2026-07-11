from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias

from src.core.proposals.models import ProposalReportResponse


class ProposalMemoReportPackageUnavailableError(Exception):
    authority = "lotus_report"
    degraded_reason = "LOTUS_REPORT_MEMO_PACKAGE_UNAVAILABLE"


ProposalMemoReportPackageRequester: TypeAlias = Callable[
    [dict[str, object]],
    ProposalReportResponse,
]

_report_package_requester: ProposalMemoReportPackageRequester | None = None


def configure_proposal_memo_report_package_requester(
    requester: ProposalMemoReportPackageRequester | None,
) -> None:
    global _report_package_requester
    _report_package_requester = requester


def request_proposal_memo_report_package(
    *,
    request: dict[str, object],
) -> ProposalReportResponse:
    if _report_package_requester is None:
        raise ProposalMemoReportPackageUnavailableError("LOTUS_REPORT_MEMO_PACKAGE_UNAVAILABLE")
    return _report_package_requester(request)


__all__ = [
    "ProposalMemoReportPackageRequester",
    "ProposalMemoReportPackageUnavailableError",
    "configure_proposal_memo_report_package_requester",
    "request_proposal_memo_report_package",
]
