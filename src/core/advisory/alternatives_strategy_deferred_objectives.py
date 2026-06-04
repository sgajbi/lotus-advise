from src.core.advisory.alternatives_normalizer import NormalizedProposalAlternativesRequest
from src.core.advisory.alternatives_strategy_base import BaseAlternativeStrategy
from src.core.advisory.alternatives_strategy_models import (
    AlternativeStrategyBuildResult,
    AlternativeStrategyInputs,
)


class AvoidRestrictedProductsStrategy(BaseAlternativeStrategy):
    strategy_id = "avoid_restricted_products_v1"
    objective = "AVOID_RESTRICTED_PRODUCTS"
    label = "Avoid restricted products"
    summary = (
        "Restricted-product alternatives remain deferred until canonical eligibility evidence "
        "is available."
    )
    required_evidence = ("RESTRICTED_PRODUCT_ELIGIBILITY", "MANDATE_CONTEXT")

    def build_result(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
    ) -> AlternativeStrategyBuildResult:
        missing_evidence = list(request.missing_evidence_reason_codes) or [
            "MISSING_RESTRICTED_PRODUCT_ELIGIBILITY"
        ]
        return AlternativeStrategyBuildResult(
            rejected_candidates=(
                self._reject(
                    inputs=inputs,
                    reason_code="ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE",
                    summary=(
                        "Restricted-product alternatives remain deferred until canonical "
                        "product eligibility evidence is available."
                    ),
                    pivot=inputs.base_currency,
                    status="REJECTED_INSUFFICIENT_EVIDENCE",
                    missing_evidence=missing_evidence,
                ),
            )
        )
