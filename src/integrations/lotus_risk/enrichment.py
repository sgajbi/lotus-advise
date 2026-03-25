import sys
from typing import cast

from src.core.models import ProposalResult, ProposalSimulateRequest


class LotusRiskEnrichmentUnavailableError(Exception):
    pass


def enrich_with_lotus_risk(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
    correlation_id: str,
) -> ProposalResult:
    main_module = sys.modules.get("src.api.main")
    if main_module is None:
        raise LotusRiskEnrichmentUnavailableError("LOTUS_RISK_ENRICHMENT_UNAVAILABLE")

    override = getattr(main_module, "enrich_with_lotus_risk", None)
    if override is None:
        raise LotusRiskEnrichmentUnavailableError("LOTUS_RISK_ENRICHMENT_UNAVAILABLE")

    enriched_result = override(
        request=request,
        proposal_result=proposal_result,
        correlation_id=correlation_id,
    )
    return cast(ProposalResult, ProposalResult.model_validate(enriched_result))
