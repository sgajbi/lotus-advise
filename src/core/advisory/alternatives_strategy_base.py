from abc import ABC, abstractmethod
from typing import Literal

from src.core.advisory.alternatives_models import (
    AlternativeCandidateSeed,
    AlternativeConstructionObjective,
    AlternativeEvidenceRequirement,
    RejectedAlternativeCandidate,
)
from src.core.advisory.alternatives_normalizer import NormalizedProposalAlternativesRequest
from src.core.advisory.alternatives_strategy_models import (
    AlternativeStrategyBuildResult,
    AlternativeStrategyInputs,
)
from src.core.advisory.alternatives_strategy_support import candidate_id


class AlternativeConstructionStrategy(ABC):
    strategy_id: str
    objective: AlternativeConstructionObjective
    required_evidence: tuple[AlternativeEvidenceRequirement, ...] = ()

    @abstractmethod
    def build_result(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
    ) -> AlternativeStrategyBuildResult:
        """Build deterministic candidate seeds without upstream service calls."""


class BaseAlternativeStrategy(AlternativeConstructionStrategy):
    label: str
    summary: str

    def _seed(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
        pivot: str,
        generated_intents: list[dict[str, object]],
        metadata: dict[str, object] | None = None,
    ) -> AlternativeCandidateSeed:
        return AlternativeCandidateSeed(
            candidate_id=candidate_id(
                objective=self.objective,
                portfolio_id=inputs.portfolio_id,
                pivot=pivot,
            ),
            objective=self.objective,
            strategy_id=self.strategy_id,
            status="READY_FOR_SIMULATION",
            label=self.label,
            summary=self.summary,
            required_evidence=list(self.required_evidence),
            generated_intents=generated_intents,
            metadata={
                "portfolio_id": inputs.portfolio_id,
                "base_currency": inputs.base_currency,
                "pivot_instrument_id": pivot,
                "objective_rank": request.requested_objectives.index(self.objective),
                **(metadata or {}),
            },
        )

    def _reject(
        self,
        *,
        inputs: AlternativeStrategyInputs,
        reason_code: str,
        summary: str,
        pivot: str,
        status: Literal["REJECTED_CONSTRAINT_VIOLATION", "REJECTED_INSUFFICIENT_EVIDENCE"],
        failed_constraints: list[str] | None = None,
        missing_evidence: list[str] | None = None,
    ) -> RejectedAlternativeCandidate:
        return RejectedAlternativeCandidate(
            candidate_id=candidate_id(
                objective=self.objective,
                portfolio_id=inputs.portfolio_id,
                pivot=pivot,
            ),
            objective=self.objective,
            status=status,
            reason_code=reason_code,
            summary=summary,
            failed_constraints=failed_constraints or [],
            missing_evidence=missing_evidence or [],
            evidence_refs=[f"strategy:{self.strategy_id}", f"portfolio:{inputs.portfolio_id}"],
        )
