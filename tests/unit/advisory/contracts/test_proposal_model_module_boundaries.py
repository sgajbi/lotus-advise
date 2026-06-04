from src.core.proposals import models
from src.core.proposals.delivery_execution_models import (
    ProposalExecutionHandoffRequest as ExecutionProposalExecutionHandoffRequest,
)
from src.core.proposals.delivery_report_models import (
    ProposalReportResponse as ReportProposalReportResponse,
)
from src.core.proposals.delivery_response_models import (
    ProposalDeliverySummaryResponse as DeliveryProposalDeliverySummaryResponse,
)
from src.core.proposals.delivery_response_models import (
    ProposalExecutionHandoffRequest as DeliveryProposalExecutionHandoffRequest,
)
from src.core.proposals.delivery_response_models import (
    ProposalReportResponse as DeliveryProposalReportResponse,
)
from src.core.proposals.delivery_summary_models import (
    ProposalDeliverySummaryResponse as SummaryProposalDeliverySummaryResponse,
)
from src.core.proposals.input_models import ProposalCreateRequest as InputProposalCreateRequest
from src.core.proposals.memo_response_models import (
    ProposalMemoResponse as MemoProposalMemoResponse,
)
from src.core.proposals.narrative_response_models import (
    ProposalNarrativeReviewResponse as NarrativeProposalNarrativeReviewResponse,
)
from src.core.proposals.operation_response_models import (
    ProposalAsyncOperationStatusResponse as OperationProposalAsyncOperationStatusResponse,
)
from src.core.proposals.persistence_models import ProposalRecord as PersistenceProposalRecord
from src.core.proposals.response_models import (
    ProposalAsyncOperationStatusResponse as ResponseProposalAsyncOperationStatusResponse,
)
from src.core.proposals.response_models import (
    ProposalCreateResponse as ResponseProposalCreateResponse,
)
from src.core.proposals.response_models import (
    ProposalMemoResponse as ResponseProposalMemoResponse,
)
from src.core.proposals.response_models import (
    ProposalNarrativeReviewResponse as ResponseProposalNarrativeReviewResponse,
)
from src.core.proposals.response_models import (
    ProposalReportResponse as ResponseProposalReportResponse,
)
from src.core.proposals.response_models import (
    ProposalWorkflowTimelineResponse as ResponseProposalWorkflowTimelineResponse,
)
from src.core.proposals.workflow_response_models import (
    ProposalWorkflowTimelineResponse as WorkflowProposalWorkflowTimelineResponse,
)


def test_proposal_models_module_preserves_public_contract_imports() -> None:
    assert models.ProposalCreateRequest is InputProposalCreateRequest
    assert models.ProposalCreateResponse is ResponseProposalCreateResponse
    assert models.ProposalReportResponse is ResponseProposalReportResponse
    assert ResponseProposalReportResponse is DeliveryProposalReportResponse
    assert DeliveryProposalReportResponse is ReportProposalReportResponse
    assert models.ProposalExecutionHandoffRequest is DeliveryProposalExecutionHandoffRequest
    assert DeliveryProposalExecutionHandoffRequest is ExecutionProposalExecutionHandoffRequest
    assert models.ProposalDeliverySummaryResponse is DeliveryProposalDeliverySummaryResponse
    assert DeliveryProposalDeliverySummaryResponse is SummaryProposalDeliverySummaryResponse
    assert models.ProposalMemoResponse is ResponseProposalMemoResponse
    assert ResponseProposalMemoResponse is MemoProposalMemoResponse
    assert models.ProposalNarrativeReviewResponse is ResponseProposalNarrativeReviewResponse
    assert ResponseProposalNarrativeReviewResponse is NarrativeProposalNarrativeReviewResponse
    assert (
        models.ProposalAsyncOperationStatusResponse is ResponseProposalAsyncOperationStatusResponse
    )
    assert (
        ResponseProposalAsyncOperationStatusResponse
        is OperationProposalAsyncOperationStatusResponse
    )
    assert models.ProposalWorkflowTimelineResponse is ResponseProposalWorkflowTimelineResponse
    assert ResponseProposalWorkflowTimelineResponse is WorkflowProposalWorkflowTimelineResponse
    assert models.ProposalRecord is PersistenceProposalRecord


def test_proposal_model_schema_titles_remain_contract_stable() -> None:
    assert models.ProposalCreateRequest.model_json_schema()["title"] == "ProposalCreateRequest"
    assert models.ProposalCreateResponse.model_json_schema()["title"] == "ProposalCreateResponse"
    assert models.ProposalRecord.model_json_schema()["title"] == "ProposalRecord"


def test_delivery_response_models_are_split_by_delivery_boundary() -> None:
    from pathlib import Path

    source_root = Path(__file__).resolve().parents[4] / "src" / "core" / "proposals"
    facade = (source_root / "delivery_response_models.py").read_text(encoding="utf-8")
    report = (source_root / "delivery_report_models.py").read_text(encoding="utf-8")
    execution = (source_root / "delivery_execution_models.py").read_text(encoding="utf-8")
    summary = (source_root / "delivery_summary_models.py").read_text(encoding="utf-8")

    for class_name in (
        "ProposalReportRequest",
        "ProposalExecutionHandoffRequest",
        "ProposalDeliverySummaryResponse",
    ):
        assert f"class {class_name}" not in facade

    assert "class ProposalReportRequest" in report
    assert "class ProposalReportResponse" in report
    assert "class ProposalExecutionHandoffRequest" in execution
    assert "class ProposalExecutionStatusResponse" in execution
    assert "class ProposalDeliveryExecutionSummary" in summary
    assert "class ProposalDeliveryHistoryResponse" in summary
