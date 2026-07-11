from typing import Any, cast

from pydantic import BaseModel, Field, ValidationError

from src.core.advisory.alternatives_models import (
    ProposalAlternative,
    RejectedAlternativeCandidate,
    validate_alternative_simulation_intent_payload,
)
from src.core.advisory.alternatives_normalizer import NormalizedProposalAlternativesRequest
from src.core.advisory.alternatives_strategies import AlternativeCandidateSeed
from src.core.common.canonical import hash_canonical_payload
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult

_SIMULATION_AUTHORITY = "lotus_core"
_RISK_AUTHORITY = "lotus_risk"
_CONSTRUCTION_POLICY_VERSION = "advisory-construction.2026-04"
_RANKING_POLICY_VERSION = "advisory-ranking.2026-04"


class AlternativesSimulationError(ValueError):
    def __init__(self, *, reason_code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.reason_code = reason_code
        self.details = details or {}


class AlternativeSimulationRecord(BaseModel):
    candidate_id: str = Field(description="Candidate identifier used for enrichment.")
    request_hash: str = Field(
        description="Canonical request hash used for the candidate evaluation."
    )
    proposal_result: ProposalResult = Field(
        description="Canonical proposal result returned by advisory orchestration."
    )


class AlternativesBatchEvaluation(BaseModel):
    alternatives: list[ProposalAlternative] = Field(
        default_factory=list,
        description="Canonical alternatives that completed simulation and risk enrichment.",
    )
    rejected_candidates: list[RejectedAlternativeCandidate] = Field(
        default_factory=list,
        description="Explicit rejected candidates generated during canonical enrichment.",
    )
    simulation_records: list[AlternativeSimulationRecord] = Field(
        default_factory=list,
        description="Canonical simulation records emitted for observability and replay wiring.",
    )


def build_alternative_simulate_request(
    *,
    base_request: ProposalSimulateRequest,
    candidate: AlternativeCandidateSeed,
) -> ProposalSimulateRequest:
    proposed_cash_flows, proposed_trades = split_candidate_simulation_intents(candidate)
    payload = base_request.model_dump(mode="json")
    payload["proposed_cash_flows"] = proposed_cash_flows
    payload["proposed_trades"] = proposed_trades
    payload["alternatives_request"] = None
    return cast(ProposalSimulateRequest, ProposalSimulateRequest.model_validate(payload))


def split_candidate_simulation_intents(
    candidate: AlternativeCandidateSeed,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    generated_intents = list(candidate.generated_intents)
    if not generated_intents:
        raise AlternativesSimulationError(
            reason_code="ALTERNATIVE_CANDIDATE_HAS_NO_INTENTS",
            message=(
                "Alternative candidate must carry deterministic generated intents before "
                "canonical simulation."
            ),
            details={"candidate_id": candidate.candidate_id},
        )

    proposed_cash_flows: list[dict[str, Any]] = []
    proposed_trades: list[dict[str, Any]] = []
    for intent in generated_intents:
        append_candidate_simulation_intent(
            candidate=candidate,
            intent=intent,
            proposed_cash_flows=proposed_cash_flows,
            proposed_trades=proposed_trades,
        )
    return proposed_cash_flows, proposed_trades


def append_candidate_simulation_intent(
    *,
    candidate: AlternativeCandidateSeed,
    intent: dict[str, Any],
    proposed_cash_flows: list[dict[str, Any]],
    proposed_trades: list[dict[str, Any]],
) -> None:
    match normalized_intent_type(intent):
        case "CASH_FLOW":
            proposed_cash_flows.append(
                validated_candidate_simulation_intent(candidate=candidate, intent=intent)
            )
        case "SECURITY_TRADE":
            proposed_trades.append(
                validated_candidate_simulation_intent(candidate=candidate, intent=intent)
            )
        case unsupported_type:
            raise AlternativesSimulationError(
                reason_code="ALTERNATIVE_INTENT_UNSUPPORTED",
                message=(
                    "Alternative candidate contains an unsupported intent type for "
                    "canonical simulation."
                ),
                details={
                    "candidate_id": candidate.candidate_id,
                    "intent_type": unsupported_type or None,
                },
            )


def validated_candidate_simulation_intent(
    *,
    candidate: AlternativeCandidateSeed,
    intent: dict[str, Any],
) -> dict[str, Any]:
    try:
        return validate_alternative_simulation_intent_payload(intent)
    except ValidationError as exc:
        raise AlternativesSimulationError(
            reason_code="ALTERNATIVE_INTENT_CONTRACT_INVALID",
            message=(
                "Alternative candidate contains a generated simulation intent that does not "
                "match the governed advisory simulation contract."
            ),
            details={
                "candidate_id": candidate.candidate_id,
                "intent_type": normalized_intent_type(intent) or None,
                "validation_error_count": len(exc.errors()),
            },
        ) from exc


def normalized_intent_type(intent: dict[str, Any]) -> str:
    return str(intent.get("intent_type", "")).upper()


def evaluate_alternative_candidates_batch(
    *,
    base_request: ProposalSimulateRequest,
    normalized_request: NormalizedProposalAlternativesRequest,
    candidates: list[AlternativeCandidateSeed],
    correlation_id: str,
    resolved_as_of: str | None = None,
    policy_context: dict[str, object] | None = None,
    evaluator: Any | None = None,
) -> AlternativesBatchEvaluation:
    evaluation = AlternativesBatchEvaluation()
    evaluated_candidates = candidates[: normalized_request.max_alternatives]
    overflow_candidates = candidates[normalized_request.max_alternatives :]
    cached_results: dict[str, ProposalAlternative | RejectedAlternativeCandidate] = {}
    cached_records: dict[str, AlternativeSimulationRecord] = {}
    evaluate = evaluator or _default_evaluator

    for candidate in evaluated_candidates:
        try:
            candidate_request = build_alternative_simulate_request(
                base_request=base_request,
                candidate=candidate,
            )
        except AlternativesSimulationError as exc:
            evaluation.rejected_candidates.append(
                _rejected_candidate(
                    candidate=candidate,
                    status="REJECTED_CONSTRAINT_VIOLATION",
                    reason_code=exc.reason_code,
                    summary=str(exc),
                    evidence_refs=[f"candidate:{candidate.candidate_id}"],
                )
            )
            continue

        candidate_request_hash = hash_canonical_payload(candidate_request.model_dump(mode="json"))
        cached_result = cached_results.get(candidate_request_hash)
        cached_record = cached_records.get(candidate_request_hash)

        if cached_result is None:
            proposal_result = evaluate(
                request=candidate_request,
                request_hash=candidate_request_hash,
                idempotency_key=None,
                correlation_id=correlation_id,
                resolved_as_of=resolved_as_of,
                policy_context=policy_context,
            )
            cached_record = AlternativeSimulationRecord(
                candidate_id=candidate.candidate_id,
                request_hash=candidate_request_hash,
                proposal_result=proposal_result,
            )
            cached_records[candidate_request_hash] = cached_record
            cached_result = _classify_candidate_result(
                candidate=candidate,
                request_hash=candidate_request_hash,
                proposal_result=proposal_result,
            )
            cached_results[candidate_request_hash] = cached_result

        _append_candidate_outcome(
            evaluation=evaluation,
            candidate=candidate,
            request_hash=candidate_request_hash,
            result=cached_result,
            simulation_record=cached_record,
        )

    for candidate in overflow_candidates:
        evaluation.rejected_candidates.append(
            _rejected_candidate(
                candidate=candidate,
                status="REJECTED_CONSTRAINT_VIOLATION",
                reason_code="ALTERNATIVE_CANDIDATE_LIMIT_EXCEEDED",
                summary=(
                    "Alternative candidate exceeded the first-implementation bounded "
                    "candidate limit."
                ),
                evidence_refs=[f"candidate:{candidate.candidate_id}"],
            )
        )

    return evaluation


def _classify_candidate_result(
    *,
    candidate: AlternativeCandidateSeed,
    request_hash: str,
    proposal_result: ProposalResult,
) -> ProposalAlternative | RejectedAlternativeCandidate:
    proposal_decision_summary = (
        proposal_result.proposal_decision_summary.model_dump(mode="json")
        if proposal_result.proposal_decision_summary is not None
        else {}
    )
    authority_rejection = unavailable_authority_rejection(
        candidate=candidate,
        request_hash=request_hash,
        proposal_result=proposal_result,
    )
    if authority_rejection is not None:
        return authority_rejection

    return ProposalAlternative(
        alternative_id=candidate.candidate_id,
        label=candidate.label,
        objective=candidate.objective,
        status=alternative_status(
            proposal_result=proposal_result,
            proposal_decision_summary=proposal_decision_summary,
        ),
        construction_policy_version=_CONSTRUCTION_POLICY_VERSION,
        ranking_policy_version=_RANKING_POLICY_VERSION,
        intents=[dict(intent) for intent in candidate.generated_intents],
        simulation_result_ref=_evidence_ref(candidate.candidate_id, "simulation"),
        risk_lens_ref=_evidence_ref(candidate.candidate_id, "risk"),
        proposal_decision_summary=proposal_decision_summary,
        evidence_refs=[
            _evidence_ref(candidate.candidate_id, "simulation"),
            _evidence_ref(candidate.candidate_id, "risk"),
            _evidence_ref(candidate.candidate_id, "decision-summary"),
            request_hash,
        ],
    )


def unavailable_authority_rejection(
    *,
    candidate: AlternativeCandidateSeed,
    request_hash: str,
    proposal_result: ProposalResult,
) -> RejectedAlternativeCandidate | None:
    authority_resolution = dict(proposal_result.explanation.get("authority_resolution", {}))
    simulation_authority = str(authority_resolution.get("simulation_authority", ""))
    risk_authority = str(authority_resolution.get("risk_authority", ""))

    if simulation_authority != _SIMULATION_AUTHORITY:
        return _rejected_candidate(
            candidate=candidate,
            status="REJECTED_SIMULATION_FAILED",
            reason_code="LOTUS_CORE_SIMULATION_UNAVAILABLE",
            summary=(
                "Canonical Lotus Core simulation authority was unavailable for this alternative."
            ),
            evidence_refs=authority_rejection_refs(candidate=candidate, request_hash=request_hash),
        )

    if risk_authority != _RISK_AUTHORITY:
        return _rejected_candidate(
            candidate=candidate,
            status="REJECTED_RISK_EVIDENCE_UNAVAILABLE",
            reason_code="LOTUS_RISK_ENRICHMENT_UNAVAILABLE",
            summary="Canonical Lotus Risk enrichment was unavailable for this alternative.",
            evidence_refs=authority_rejection_refs(candidate=candidate, request_hash=request_hash),
        )

    return None


def authority_rejection_refs(
    *,
    candidate: AlternativeCandidateSeed,
    request_hash: str,
) -> list[str]:
    return [
        f"candidate:{candidate.candidate_id}",
        request_hash,
        "proposal.explanation.authority_resolution",
    ]


def alternative_status(
    *,
    proposal_result: ProposalResult,
    proposal_decision_summary: dict[str, Any],
) -> str:
    decision_status = str(proposal_decision_summary.get("decision_status", ""))
    if decision_status in {"BLOCKED_REMEDIATION_REQUIRED", "INSUFFICIENT_EVIDENCE"}:
        return "REJECTED_POLICY_BLOCKED"
    if proposal_result.status == "READY":
        return "FEASIBLE"
    return "FEASIBLE_WITH_REVIEW"


def _append_candidate_outcome(
    *,
    evaluation: AlternativesBatchEvaluation,
    candidate: AlternativeCandidateSeed,
    request_hash: str,
    result: ProposalAlternative | RejectedAlternativeCandidate,
    simulation_record: AlternativeSimulationRecord | None,
) -> None:
    cloned_result = result.model_copy(deep=True)
    if isinstance(cloned_result, ProposalAlternative):
        cloned_result.alternative_id = candidate.candidate_id
        cloned_result.label = candidate.label
        cloned_result.objective = candidate.objective
        cloned_result.intents = [dict(intent) for intent in candidate.generated_intents]
        cloned_result.simulation_result_ref = _evidence_ref(candidate.candidate_id, "simulation")
        cloned_result.risk_lens_ref = _evidence_ref(candidate.candidate_id, "risk")
        cloned_result.evidence_refs = [
            _evidence_ref(candidate.candidate_id, "simulation"),
            _evidence_ref(candidate.candidate_id, "risk"),
            _evidence_ref(candidate.candidate_id, "decision-summary"),
            request_hash,
        ]
        evaluation.alternatives.append(cloned_result)
    else:
        cloned_result.candidate_id = candidate.candidate_id
        cloned_result.objective = candidate.objective
        cloned_result.evidence_refs = [f"candidate:{candidate.candidate_id}", request_hash]
        evaluation.rejected_candidates.append(cloned_result)

    if simulation_record is not None:
        evaluation.simulation_records.append(
            simulation_record.model_copy(update={"candidate_id": candidate.candidate_id}, deep=True)
        )


def _rejected_candidate(
    *,
    candidate: AlternativeCandidateSeed,
    status: str,
    reason_code: str,
    summary: str,
    evidence_refs: list[str],
) -> RejectedAlternativeCandidate:
    return RejectedAlternativeCandidate(
        candidate_id=candidate.candidate_id,
        objective=candidate.objective,
        status=status,
        reason_code=reason_code,
        summary=summary,
        evidence_refs=evidence_refs,
    )


def _evidence_ref(candidate_id: str, evidence_key: str) -> str:
    return f"evidence://proposal-alternatives/{candidate_id}/{evidence_key}"


def _default_evaluator(**kwargs: Any) -> ProposalResult:
    from src.core.advisory.orchestration import evaluate_advisory_proposal

    return evaluate_advisory_proposal(**kwargs)
