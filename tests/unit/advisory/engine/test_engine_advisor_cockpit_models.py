from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.advisor_cockpit import (
    COCKPIT_ACTION_DEFAULT_PAGE_SIZE,
    COCKPIT_ACTION_MAX_PAGE_SIZE,
    AdvisorCockpitActionFamily,
    AdvisorCockpitActionPriority,
    AdvisorCockpitActionStatus,
    AdvisorCockpitOperatingSnapshot,
    AdvisorCockpitOwnerRole,
    AdvisoryActionItem,
    CockpitAcknowledgementState,
    CockpitCallerContext,
    CockpitEvidenceRef,
    cockpit_cursor_start,
    normalize_cockpit_page_size,
    sort_cockpit_action_items,
)
from src.core.advisor_cockpit.action_models import (
    AdvisoryActionItem as FocusedAdvisoryActionItem,
)
from src.core.advisor_cockpit.action_models import (
    AdvisoryActionItemPage as FocusedAdvisoryActionItemPage,
)
from src.core.advisor_cockpit.models import (
    AdvisorCockpitActionFamily as CompatibilityAdvisorCockpitActionFamily,
)
from src.core.advisor_cockpit.models import (
    AdvisorCockpitActionPriority as CompatibilityAdvisorCockpitActionPriority,
)
from src.core.advisor_cockpit.models import (
    AdvisorCockpitActionStatus as CompatibilityAdvisorCockpitActionStatus,
)
from src.core.advisor_cockpit.models import (
    AdvisorCockpitOperatingSnapshot as CompatibilityAdvisorCockpitOperatingSnapshot,
)
from src.core.advisor_cockpit.models import (
    AdvisorCockpitOwnerRole as CompatibilityAdvisorCockpitOwnerRole,
)
from src.core.advisor_cockpit.models import (
    AdvisoryActionItem as CompatibilityAdvisoryActionItem,
)
from src.core.advisor_cockpit.models import (
    AdvisoryActionItemPage as CompatibilityAdvisoryActionItemPage,
)
from src.core.advisor_cockpit.models import (
    CockpitAcknowledgementState as CompatibilityCockpitAcknowledgementState,
)
from src.core.advisor_cockpit.models import (
    CockpitCallerContext as CompatibilityCockpitCallerContext,
)
from src.core.advisor_cockpit.models import (
    CockpitEvidenceRef as CompatibilityCockpitEvidenceRef,
)
from src.core.advisor_cockpit.models import (
    MeetingPreparationPacket as CompatibilityMeetingPreparationPacket,
)
from src.core.advisor_cockpit.reference_models import (
    CockpitAcknowledgementState as FocusedCockpitAcknowledgementState,
)
from src.core.advisor_cockpit.reference_models import (
    CockpitCallerContext as FocusedCockpitCallerContext,
)
from src.core.advisor_cockpit.reference_models import (
    CockpitEvidenceRef as FocusedCockpitEvidenceRef,
)
from src.core.advisor_cockpit.snapshot_models import (
    AdvisorCockpitOperatingSnapshot as FocusedAdvisorCockpitOperatingSnapshot,
)
from src.core.advisor_cockpit.snapshot_models import (
    MeetingPreparationPacket as FocusedMeetingPreparationPacket,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitActionFamily as FocusedAdvisorCockpitActionFamily,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitActionPriority as FocusedAdvisorCockpitActionPriority,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitActionStatus as FocusedAdvisorCockpitActionStatus,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitOwnerRole as FocusedAdvisorCockpitOwnerRole,
)
from src.core.proposals.exceptions import ProposalValidationError


def _action(
    action_item_id: str,
    *,
    priority: str = "MEDIUM",
    status: str = "READY",
    family: str = "CLIENT_MEETING_PREPARATION",
    due_at: str | None = None,
    sla_age_band: str = "NOT_APPLICABLE",
    materiality_rank: int = 0,
) -> AdvisoryActionItem:
    return AdvisoryActionItem(
        action_item_id=action_item_id,
        action_item_version=1,
        action_family=family,
        status=status,
        priority=priority,
        owner_role="ADVISOR",
        owning_system="lotus-advise",
        title="Review advisory action",
        next_required_action="Review the source-backed advisory evidence.",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        due_at=due_at,
        sla_age_band=sla_age_band,
        materiality_rank=materiality_rank,
    )


def test_advisor_cockpit_models_expose_private_banking_contract_vocabulary() -> None:
    schema = AdvisorCockpitOperatingSnapshot.model_json_schema()
    definitions = schema["$defs"]

    action_schema = definitions["AdvisoryActionItem"]
    assert action_schema["properties"]["priority"]["examples"] == ["HIGH"]
    assert action_schema["properties"]["portfolio_id"]["examples"] == ["PB_SG_GLOBAL_BAL_001"]
    assert (
        "Workbench must render, not infer"
        in action_schema["properties"]["next_required_action"]["description"]
    )

    unsupported = schema["properties"]["unsupported_capabilities"]["items"]["enum"]
    assert "CLIENT_READY_PUBLICATION" in unsupported
    assert "FULL_RFC0028_DEMO_RFP_PACKAGE" in unsupported


def test_advisor_cockpit_models_preserve_type_import_contract() -> None:
    assert AdvisorCockpitActionFamily is FocusedAdvisorCockpitActionFamily
    assert AdvisorCockpitActionPriority is FocusedAdvisorCockpitActionPriority
    assert AdvisorCockpitActionStatus is FocusedAdvisorCockpitActionStatus
    assert AdvisorCockpitOwnerRole is FocusedAdvisorCockpitOwnerRole
    assert CompatibilityAdvisorCockpitActionFamily is FocusedAdvisorCockpitActionFamily
    assert CompatibilityAdvisorCockpitActionPriority is FocusedAdvisorCockpitActionPriority
    assert CompatibilityAdvisorCockpitActionStatus is FocusedAdvisorCockpitActionStatus
    assert CompatibilityAdvisorCockpitOwnerRole is FocusedAdvisorCockpitOwnerRole


def test_advisor_cockpit_models_preserve_reference_import_contract() -> None:
    assert CockpitAcknowledgementState is FocusedCockpitAcknowledgementState
    assert CockpitCallerContext is FocusedCockpitCallerContext
    assert CockpitEvidenceRef is FocusedCockpitEvidenceRef
    assert CompatibilityCockpitAcknowledgementState is FocusedCockpitAcknowledgementState
    assert CompatibilityCockpitCallerContext is FocusedCockpitCallerContext
    assert CompatibilityCockpitEvidenceRef is FocusedCockpitEvidenceRef


def test_advisor_cockpit_models_preserve_action_import_contract() -> None:
    assert AdvisoryActionItem is FocusedAdvisoryActionItem
    assert CompatibilityAdvisoryActionItem is FocusedAdvisoryActionItem
    assert CompatibilityAdvisoryActionItemPage is FocusedAdvisoryActionItemPage


def test_advisor_cockpit_models_preserve_snapshot_import_contract() -> None:
    assert AdvisorCockpitOperatingSnapshot is FocusedAdvisorCockpitOperatingSnapshot
    assert CompatibilityAdvisorCockpitOperatingSnapshot is FocusedAdvisorCockpitOperatingSnapshot
    assert CompatibilityMeetingPreparationPacket is FocusedMeetingPreparationPacket


def test_advisor_cockpit_models_is_pure_compatibility_facade() -> None:
    tree = ast.parse(Path("src/core/advisor_cockpit/models.py").read_text(encoding="utf-8"))

    assert not [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert not [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]


def test_advisor_cockpit_sorting_matches_rfc0026_stable_order() -> None:
    actions = [
        _action("a-low", priority="LOW", status="READY", due_at="2026-05-28T08:00:00+00:00"),
        _action(
            "a-high-lower-materiality",
            priority="HIGH",
            status="PENDING_REVIEW",
            family="POLICY_REVIEW_REQUIRED",
            due_at="2026-05-27T08:00:00+00:00",
            sla_age_band="OVERDUE",
            materiality_rank=10,
        ),
        _action(
            "a-high-higher-materiality",
            priority="HIGH",
            status="PENDING_REVIEW",
            family="POLICY_REVIEW_REQUIRED",
            due_at="2026-05-27T08:00:00+00:00",
            sla_age_band="OVERDUE",
            materiality_rank=50,
        ),
        _action("a-critical", priority="CRITICAL", status="BLOCKED"),
    ]

    sorted_ids = [item.action_item_id for item in sort_cockpit_action_items(actions)]

    assert sorted_ids == [
        "a-critical",
        "a-high-higher-materiality",
        "a-high-lower-materiality",
        "a-low",
    ]


def test_advisor_cockpit_page_size_is_bounded_for_large_books() -> None:
    assert COCKPIT_ACTION_DEFAULT_PAGE_SIZE == 25
    assert COCKPIT_ACTION_MAX_PAGE_SIZE == 100
    assert normalize_cockpit_page_size(None) == 25
    assert normalize_cockpit_page_size(0) == 25
    assert normalize_cockpit_page_size(250) == 100
    assert normalize_cockpit_page_size(50) == 50


def test_advisor_cockpit_cursor_start_is_reusable_and_validated() -> None:
    actions = [_action("a-1"), _action("a-2"), _action("a-3")]

    assert (
        cockpit_cursor_start(
            items=actions,
            cursor=None,
            identity=lambda action: action.action_item_id,
            invalid_code="ADVISOR_COCKPIT_CURSOR_INVALID",
        )
        == 0
    )
    assert (
        cockpit_cursor_start(
            items=actions,
            cursor="a-2",
            identity=lambda action: action.action_item_id,
            invalid_code="ADVISOR_COCKPIT_CURSOR_INVALID",
        )
        == 2
    )

    try:
        cockpit_cursor_start(
            items=actions,
            cursor="missing-action",
            identity=lambda action: action.action_item_id,
            invalid_code="ADVISOR_COCKPIT_CURSOR_INVALID",
        )
    except ProposalValidationError as exc:
        assert str(exc) == "ADVISOR_COCKPIT_CURSOR_INVALID"
    else:
        raise AssertionError("missing action cursor should fail validation")


def test_advisor_cockpit_core_package_has_no_api_or_ui_dependency() -> None:
    package_root = Path("src/core/advisor_cockpit")
    forbidden_prefixes = ("src.api", "src.integrations", "src.infrastructure")

    for path in package_root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        imported_roots = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        assert not any(
            module.startswith(forbidden_prefixes) for module in imported_modules | imported_roots
        ), path


def test_advisor_cockpit_snapshot_uses_server_side_caller_context() -> None:
    snapshot = AdvisorCockpitOperatingSnapshot(
        snapshot_id="cockpit_snapshot_sg_001",
        caller_context=CockpitCallerContext(
            advisor_id="advisor_sg_001",
            role="ADVISOR",
            demo_context=True,
        ),
        as_of="2026-05-27T08:00:00+00:00",
        top_priority_actions=[_action("a-policy", priority="HIGH", status="PENDING_REVIEW")],
        unsupported_capabilities=["CLIENT_READY_PUBLICATION"],
    )

    assert snapshot.caller_context.advisor_id == "advisor_sg_001"
    assert snapshot.top_priority_actions[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert snapshot.unsupported_capabilities == ["CLIENT_READY_PUBLICATION"]


def test_advisor_cockpit_models_reject_sensitive_or_oversized_business_copy() -> None:
    with pytest.raises(ValidationError, match="sensitive technical detail"):
        CockpitEvidenceRef(
            evidence_id="policy_eval_sg_001",
            evidence_type="POLICY_EVALUATION",
            source_system="lotus-advise",
            access_class="RESTRICTED_CUSTOMER_EVIDENCE",
            summary="Raw prompt material is available for advisor review.",
        )

    with pytest.raises(ValidationError, match="sensitive technical detail"):
        CockpitEvidenceRef(
            evidence_id="policy_eval_sg_001",
            evidence_type="POLICY_EVALUATION",
            source_system="lotus-advise",
            access_class="RESTRICTED_CUSTOMER_EVIDENCE",
            summary="raw_payload retained with trace_id for operator diagnosis.",
        )

    with pytest.raises(ValidationError, match="sensitive technical detail"):
        AdvisoryActionItem(
            action_item_id="aci_meeting_001",
            action_item_version=1,
            action_family="CLIENT_MEETING_PREPARATION",
            status="READY",
            priority="MEDIUM",
            owner_role="ADVISOR",
            owning_system="lotus-advise",
            title="Trace_id retained for follow up",
            next_required_action="Review the source-backed advisory evidence.",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            sla_age_band="NOT_APPLICABLE",
        )

    with pytest.raises(ValidationError):
        _action("x" * 161)


def test_advisor_cockpit_unacknowledged_state_cannot_carry_acknowledgement_detail() -> None:
    with pytest.raises(ValidationError, match="unacknowledged cockpit state"):
        CockpitAcknowledgementState(
            acknowledged=False,
            acknowledgement_id="ack_001",
            acknowledged_by="advisor_sg_001",
            acknowledged_at="2026-05-27T08:00:00+00:00",
        )


def test_advisor_cockpit_snapshot_rejects_invalid_action_counts() -> None:
    with pytest.raises(ValidationError, match="action counts cannot be negative"):
        AdvisorCockpitOperatingSnapshot(
            snapshot_id="cockpit_snapshot_sg_001",
            caller_context=CockpitCallerContext(role="ADVISOR"),
            as_of="2026-05-27T08:00:00+00:00",
            action_counts={"status.PENDING_REVIEW": -1},
        )
