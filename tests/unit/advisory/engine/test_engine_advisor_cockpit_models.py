from __future__ import annotations

import ast
from pathlib import Path

from src.core.advisor_cockpit import (
    COCKPIT_ACTION_DEFAULT_PAGE_SIZE,
    COCKPIT_ACTION_MAX_PAGE_SIZE,
    AdvisorCockpitOperatingSnapshot,
    AdvisoryActionItem,
    CockpitCallerContext,
    normalize_cockpit_page_size,
    sort_cockpit_action_items,
)


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
