from src.core.policy_packs.catalog_models import (
    PolicyPackActivationRequest as CatalogPolicyPackActivationRequest,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackActivationResponse as CatalogPolicyPackActivationResponse,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackAuditEvent as CatalogPolicyPackAuditEvent,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackDetailResponse as CatalogPolicyPackDetailResponse,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackListResponse as CatalogPolicyPackListResponse,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackSummary as CatalogPolicyPackSummary,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackValidationRequest as CatalogPolicyPackValidationRequest,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackValidationResponse as CatalogPolicyPackValidationResponse,
)
from src.core.policy_packs.evaluation_models import (
    PolicyPackApplicabilityResult as EvaluationPolicyPackApplicabilityResult,
)
from src.core.policy_packs.evaluation_models import (
    PolicyPackEvaluationResponse as EvaluationPolicyPackEvaluationResponse,
)
from src.core.policy_packs.evaluation_models import (
    PolicyRuleEvaluationResult as EvaluationPolicyRuleEvaluationResult,
)
from src.core.policy_packs.models import (
    PolicyPackActivationRequest,
    PolicyPackActivationResponse,
    PolicyPackApplicabilityResult,
    PolicyPackAuditEvent,
    PolicyPackDetailResponse,
    PolicyPackEvaluationResponse,
    PolicyPackListResponse,
    PolicyPackSummary,
    PolicyPackValidationRequest,
    PolicyPackValidationResponse,
    PolicyRuleEvaluationResult,
)


def test_policy_pack_models_preserves_catalog_model_import_contract():
    assert PolicyPackActivationRequest is CatalogPolicyPackActivationRequest
    assert PolicyPackActivationResponse is CatalogPolicyPackActivationResponse
    assert PolicyPackAuditEvent is CatalogPolicyPackAuditEvent
    assert PolicyPackDetailResponse is CatalogPolicyPackDetailResponse
    assert PolicyPackListResponse is CatalogPolicyPackListResponse
    assert PolicyPackSummary is CatalogPolicyPackSummary
    assert PolicyPackValidationRequest is CatalogPolicyPackValidationRequest
    assert PolicyPackValidationResponse is CatalogPolicyPackValidationResponse


def test_policy_pack_models_preserves_evaluation_model_import_contract():
    assert PolicyPackApplicabilityResult is EvaluationPolicyPackApplicabilityResult
    assert PolicyPackEvaluationResponse is EvaluationPolicyPackEvaluationResponse
    assert PolicyRuleEvaluationResult is EvaluationPolicyRuleEvaluationResult
