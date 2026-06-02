from src.core.advisory.artifact_models import (
    ProposalArtifactRiskLens,
    ProposalArtifactSuitabilityHighlight,
    ProposalArtifactSuitabilitySummary,
)
from src.core.advisory.risk_lens import extract_risk_lens
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult


def build_suitability_summary(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> ProposalArtifactSuitabilitySummary:
    if not request.options.enable_suitability_scanner or result.suitability is None:
        return ProposalArtifactSuitabilitySummary(
            status="NOT_AVAILABLE",
            new_issues=0,
            resolved_issues=0,
            persistent_issues=0,
            highest_severity_new=None,
            highlights=[],
            issues=[],
        )

    highlights = [
        ProposalArtifactSuitabilityHighlight(
            code=issue.status_change,
            text=f"{issue.status_change.title()} issue: {issue.issue_id}.",
        )
        for issue in result.suitability.issues[: request.options.drift_top_contributors_limit]
    ]
    return ProposalArtifactSuitabilitySummary(
        status="AVAILABLE",
        new_issues=result.suitability.summary.new_count,
        resolved_issues=result.suitability.summary.resolved_count,
        persistent_issues=result.suitability.summary.persistent_count,
        highest_severity_new=result.suitability.summary.highest_severity_new,
        highlights=highlights,
        issues=result.suitability.issues,
    )


def build_risk_lens_summary(result: ProposalResult) -> ProposalArtifactRiskLens:
    risk_lens = extract_risk_lens(result)
    if risk_lens is None:
        return ProposalArtifactRiskLens(
            status="NOT_AVAILABLE",
            source_service=None,
            summary="Concentration risk lens is unavailable for this proposal run.",
            highlights=[],
        )

    single_position = risk_lens.get("single_position_concentration", {})
    issuer = risk_lens.get("issuer_concentration", {})
    return ProposalArtifactRiskLens(
        status="AVAILABLE",
        source_service=str(risk_lens["source_service"]),
        summary=(
            "Concentration risk lens is available from lotus-risk with before/after "
            "single-name and issuer concentration measures."
        ),
        highlights=[
            (
                "Top position weight changes from "
                f"{single_position.get('top_position_weight_current')} to "
                f"{single_position.get('top_position_weight_proposed')}."
            ),
            (
                "Issuer concentration HHI changes from "
                f"{issuer.get('hhi_current')} to {issuer.get('hhi_proposed')}."
            ),
        ],
    )
