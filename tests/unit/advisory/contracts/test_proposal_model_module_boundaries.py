from src.core.proposals import models
from src.core.proposals.delivery_response_models import (
    ProposalReportResponse as DeliveryProposalReportResponse,
)
from src.core.proposals.input_models import ProposalCreateRequest as InputProposalCreateRequest
from src.core.proposals.persistence_models import ProposalRecord as PersistenceProposalRecord
from src.core.proposals.response_models import (
    ProposalCreateResponse as ResponseProposalCreateResponse,
)
from src.core.proposals.response_models import (
    ProposalReportResponse as ResponseProposalReportResponse,
)


def test_proposal_models_module_preserves_public_contract_imports() -> None:
    assert models.ProposalCreateRequest is InputProposalCreateRequest
    assert models.ProposalCreateResponse is ResponseProposalCreateResponse
    assert models.ProposalReportResponse is ResponseProposalReportResponse
    assert ResponseProposalReportResponse is DeliveryProposalReportResponse
    assert models.ProposalRecord is PersistenceProposalRecord


def test_proposal_model_schema_titles_remain_contract_stable() -> None:
    assert models.ProposalCreateRequest.model_json_schema()["title"] == "ProposalCreateRequest"
    assert models.ProposalCreateResponse.model_json_schema()["title"] == "ProposalCreateResponse"
    assert models.ProposalRecord.model_json_schema()["title"] == "ProposalRecord"
