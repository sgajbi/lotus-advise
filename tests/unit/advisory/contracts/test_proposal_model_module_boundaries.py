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
from src.core.proposals.input_context_models import (
    ProposalCreateMetadata as ContextProposalCreateMetadata,
)
from src.core.proposals.input_context_models import (
    ProposalResolvedContext as ContextProposalResolvedContext,
)
from src.core.proposals.input_context_models import (
    ProposalStatefulInput as ContextProposalStatefulInput,
)
from src.core.proposals.input_context_models import (
    ProposalStatelessInput as ContextProposalStatelessInput,
)
from src.core.proposals.input_models import ProposalCreateRequest as InputProposalCreateRequest
from src.core.proposals.input_models import (
    ProposalResolvedContext as InputProposalResolvedContext,
)
from src.core.proposals.input_request_models import (
    ProposalCreateRequest as RequestProposalCreateRequest,
)
from src.core.proposals.input_request_models import (
    ProposalSimulationRequest as RequestProposalSimulationRequest,
)
from src.core.proposals.input_request_models import (
    ProposalVersionRequest as RequestProposalVersionRequest,
)
from src.core.proposals.memo_event_models import (
    ProposalMemoAuditEvent as EventProposalMemoAuditEvent,
)
from src.core.proposals.memo_lineage_response_models import (
    ProposalMemoLineageItem as LineageProposalMemoLineageItem,
)
from src.core.proposals.memo_lineage_response_models import (
    ProposalMemoLineageResponse as LineageProposalMemoLineageResponse,
)
from src.core.proposals.memo_lineage_response_models import (
    ProposalMemoReplayEvidenceResponse as LineageProposalMemoReplayEvidenceResponse,
)
from src.core.proposals.memo_request_models import (
    ProposalMemoAiCommentaryRequest as RequestProposalMemoAiCommentaryRequest,
)
from src.core.proposals.memo_request_models import (
    ProposalMemoCreateRequest as RequestProposalMemoCreateRequest,
)
from src.core.proposals.memo_request_models import (
    ProposalMemoReportPackageEventRequest as RequestProposalMemoReportPackageEventRequest,
)
from src.core.proposals.memo_request_models import (
    ProposalMemoReportPackageRequest as RequestProposalMemoReportPackageRequest,
)
from src.core.proposals.memo_request_models import (
    ProposalMemoReviewRequest as RequestProposalMemoReviewRequest,
)
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
    ProposalMemoAiCommentaryRequest as ResponseProposalMemoAiCommentaryRequest,
)
from src.core.proposals.response_models import (
    ProposalMemoAuditEvent as ResponseProposalMemoAuditEvent,
)
from src.core.proposals.response_models import (
    ProposalMemoCreateRequest as ResponseProposalMemoCreateRequest,
)
from src.core.proposals.response_models import (
    ProposalMemoLineageItem as ResponseProposalMemoLineageItem,
)
from src.core.proposals.response_models import (
    ProposalMemoLineageResponse as ResponseProposalMemoLineageResponse,
)
from src.core.proposals.response_models import (
    ProposalMemoReplayEvidenceResponse as ResponseProposalMemoReplayEvidenceResponse,
)
from src.core.proposals.response_models import (
    ProposalMemoReportPackageEventRequest as ResponseProposalMemoReportPackageEventRequest,
)
from src.core.proposals.response_models import (
    ProposalMemoReportPackageRequest as ResponseProposalMemoReportPackageRequest,
)
from src.core.proposals.response_models import (
    ProposalMemoResponse as ResponseProposalMemoResponse,
)
from src.core.proposals.response_models import (
    ProposalMemoReviewRequest as ResponseProposalMemoReviewRequest,
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
    assert InputProposalCreateRequest is RequestProposalCreateRequest
    assert models.ProposalSimulationRequest is RequestProposalSimulationRequest
    assert models.ProposalVersionRequest is RequestProposalVersionRequest
    assert models.ProposalCreateMetadata is ContextProposalCreateMetadata
    assert models.ProposalStatelessInput is ContextProposalStatelessInput
    assert models.ProposalStatefulInput is ContextProposalStatefulInput
    assert models.ProposalResolvedContext is InputProposalResolvedContext
    assert InputProposalResolvedContext is ContextProposalResolvedContext
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
    assert models.ProposalMemoAuditEvent is ResponseProposalMemoAuditEvent
    assert ResponseProposalMemoAuditEvent is EventProposalMemoAuditEvent
    assert models.ProposalMemoLineageItem is ResponseProposalMemoLineageItem
    assert ResponseProposalMemoLineageItem is LineageProposalMemoLineageItem
    assert models.ProposalMemoLineageResponse is ResponseProposalMemoLineageResponse
    assert ResponseProposalMemoLineageResponse is LineageProposalMemoLineageResponse
    assert models.ProposalMemoReplayEvidenceResponse is ResponseProposalMemoReplayEvidenceResponse
    assert ResponseProposalMemoReplayEvidenceResponse is LineageProposalMemoReplayEvidenceResponse
    assert models.ProposalMemoCreateRequest is ResponseProposalMemoCreateRequest
    assert ResponseProposalMemoCreateRequest is RequestProposalMemoCreateRequest
    assert models.ProposalMemoReviewRequest is ResponseProposalMemoReviewRequest
    assert ResponseProposalMemoReviewRequest is RequestProposalMemoReviewRequest
    assert (
        models.ProposalMemoReportPackageEventRequest
        is ResponseProposalMemoReportPackageEventRequest
    )
    assert (
        ResponseProposalMemoReportPackageEventRequest
        is RequestProposalMemoReportPackageEventRequest
    )
    assert models.ProposalMemoReportPackageRequest is ResponseProposalMemoReportPackageRequest
    assert ResponseProposalMemoReportPackageRequest is RequestProposalMemoReportPackageRequest
    assert models.ProposalMemoAiCommentaryRequest is ResponseProposalMemoAiCommentaryRequest
    assert ResponseProposalMemoAiCommentaryRequest is RequestProposalMemoAiCommentaryRequest
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


def test_proposal_input_models_are_split_by_context_and_request_boundary() -> None:
    from pathlib import Path

    source_root = Path(__file__).resolve().parents[4] / "src" / "core" / "proposals"
    facade = (source_root / "input_models.py").read_text(encoding="utf-8")
    contexts = (source_root / "input_context_models.py").read_text(encoding="utf-8")
    requests = (source_root / "input_request_models.py").read_text(encoding="utf-8")

    for class_name in (
        "ProposalCreateMetadata",
        "ProposalStatelessInput",
        "ProposalStatefulInput",
        "ProposalResolvedContext",
        "ProposalSimulationRequest",
        "ProposalCreateRequest",
        "ProposalVersionRequest",
    ):
        assert f"class {class_name}" not in facade

    for class_name in (
        "ProposalCreateMetadata",
        "ProposalStatelessInput",
        "ProposalStatefulInput",
        "ProposalResolvedContext",
    ):
        assert f"class {class_name}" in contexts

    for class_name in (
        "ProposalSimulationRequest",
        "ProposalCreateRequest",
        "ProposalVersionRequest",
    ):
        assert f"class {class_name}" in requests


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


def test_memo_request_models_are_split_from_memo_response_boundary() -> None:
    from pathlib import Path

    source_root = Path(__file__).resolve().parents[4] / "src" / "core" / "proposals"
    facade = (source_root / "memo_response_models.py").read_text(encoding="utf-8")
    requests = (source_root / "memo_request_models.py").read_text(encoding="utf-8")
    types = (source_root / "memo_types.py").read_text(encoding="utf-8")

    for class_name in (
        "ProposalMemoCreateRequest",
        "ProposalMemoReviewRequest",
        "ProposalMemoReportPackageEventRequest",
        "ProposalMemoReportPackageRequest",
        "ProposalMemoAiCommentaryRequest",
    ):
        assert f"class {class_name}" not in facade
        assert f"class {class_name}" in requests

    assert "ProposalMemoReviewAction = Literal" in types
    assert "ProposalMemoCommentarySection = Literal" in types


def test_memo_event_model_is_split_from_memo_response_boundary() -> None:
    from pathlib import Path

    source_root = Path(__file__).resolve().parents[4] / "src" / "core" / "proposals"
    facade = (source_root / "memo_response_models.py").read_text(encoding="utf-8")
    event_models = (source_root / "memo_event_models.py").read_text(encoding="utf-8")

    assert "class ProposalMemoAuditEvent" not in facade
    assert "class ProposalMemoAuditEvent" in event_models


def test_memo_lineage_models_are_split_from_memo_response_boundary() -> None:
    from pathlib import Path

    source_root = Path(__file__).resolve().parents[4] / "src" / "core" / "proposals"
    facade = (source_root / "memo_response_models.py").read_text(encoding="utf-8")
    lineage_models = (source_root / "memo_lineage_response_models.py").read_text(encoding="utf-8")

    for class_name in (
        "ProposalMemoLineageItem",
        "ProposalMemoLineageResponse",
        "ProposalMemoReplayEvidenceResponse",
    ):
        assert f"class {class_name}" not in facade
        assert f"class {class_name}" in lineage_models
