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
    PolicyEvaluationAuditEvent,
    PolicyEvaluationCreateRequest,
    PolicyEvaluationEventRequest,
    PolicyEvaluationPersistenceResult,
    PolicyEvaluationRecord,
    PolicyEvaluationReplayRequest,
    PolicyEvaluationReplayResponse,
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
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationAuditEvent as PersistencePolicyEvaluationAuditEvent,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationCreateRequest as PersistencePolicyEvaluationCreateRequest,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationEventRequest as PersistencePolicyEvaluationEventRequest,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationPersistenceResult as PersistencePolicyEvaluationPersistenceResult,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationRecord as PersistencePolicyEvaluationRecord,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationReplayRequest as PersistencePolicyEvaluationReplayRequest,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationReplayResponse as PersistencePolicyEvaluationReplayResponse,
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


def test_policy_pack_models_preserves_persistence_model_import_contract():
    assert PolicyEvaluationAuditEvent is PersistencePolicyEvaluationAuditEvent
    assert PolicyEvaluationCreateRequest is PersistencePolicyEvaluationCreateRequest
    assert PolicyEvaluationEventRequest is PersistencePolicyEvaluationEventRequest
    assert PolicyEvaluationPersistenceResult is PersistencePolicyEvaluationPersistenceResult
    assert PolicyEvaluationRecord is PersistencePolicyEvaluationRecord
    assert PolicyEvaluationReplayRequest is PersistencePolicyEvaluationReplayRequest
    assert PolicyEvaluationReplayResponse is PersistencePolicyEvaluationReplayResponse
