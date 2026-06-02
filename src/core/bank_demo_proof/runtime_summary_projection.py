from __future__ import annotations

from typing import Any

from src.core.bank_demo_proof.runtime_summary_access import dict_at, select_fields


def build_proposal_lifecycle_summary(parity: dict[str, Any]) -> dict[str, Any]:
    return {
        "sync_state": parity.get("lifecycle_current_state"),
        "sync_latest_version": parity.get("lifecycle_latest_version_no"),
        "async_state": parity.get("async_lifecycle_current_state"),
        "async_latest_version": parity.get("async_lifecycle_latest_version_no"),
        "execution_handoff_status": parity.get("execution_handoff_status"),
        "execution_terminal_status": parity.get("execution_terminal_status"),
        "report_status": parity.get("report_status"),
    }


def build_workspace_rationale_summary(parity: dict[str, Any]) -> dict[str, Any]:
    return {
        "initial_run_recorded": bool(parity.get("workspace_rationale_initial_run_id")),
        "replacement_run_recorded": bool(parity.get("workspace_rationale_replacement_run_id")),
        "review_state": parity.get("workspace_rationale_review_state"),
        "supportability_status": parity.get("workspace_rationale_supportability_status"),
    }


def build_proposal_narrative_summary(parity: dict[str, Any]) -> dict[str, Any]:
    return select_fields(
        dict_at(parity, "proposal_narrative"),
        (
            "generation_mode",
            "policy_status",
            "read_posture_source",
            "regeneration_persistence_status",
            "review_state",
            "client_ready_status",
            "report_status",
            "report_package_status",
            "guardrail_failure_status",
            "ai_assisted_status",
        ),
    )


def build_proposal_memo_summary(parity: dict[str, Any]) -> dict[str, Any]:
    return select_fields(
        dict_at(parity, "proposal_memo"),
        (
            "memo_status",
            "lifecycle_status",
            "projection_client_ready_publication",
            "review_action",
            "review_client_ready_publication",
            "report_status",
            "report_package_status",
            "requested_output_formats",
            "render_ref_status",
            "archive_ref_status",
            "archive_retention_posture",
            "archive_legal_hold_posture",
            "archive_access_audit_ref_status",
            "ai_status",
            "ai_authoritative_for_memo_status",
            "ai_review_required",
            "lineage_complete",
            "replay_client_ready_publication",
            "stale_hash_block_status",
            "client_ready_release_block_status",
            "client_ready_document_block_status",
        ),
    )


def build_proposal_policy_summary(parity: dict[str, Any]) -> dict[str, Any]:
    return select_fields(
        dict_at(parity, "proposal_policy"),
        (
            "policy_pack_id",
            "policy_version",
            "evaluation_status",
            "material_rule_count",
            "pending_rule_count",
            "approval_dependency_count",
            "disclosure_requirement_count",
            "consent_requirement_count",
            "source_ref_count",
            "source_gap_count",
            "workflow_sign_off_status",
            "workflow_client_ready_publication",
            "workflow_open_requirement_count",
            "sign_off_decision_status",
            "report_status",
            "report_package_status",
            "requested_output_formats",
            "render_ref_status",
            "archive_ref_status",
            "archive_retention_posture",
            "archive_legal_hold_posture",
            "archive_access_audit_ref_status",
            "ai_status",
            "ai_authoritative_for_policy_status",
            "ai_human_review_required",
            "ai_raw_source_evidence_included",
            "lineage_complete",
            "replay_evaluation_hash_matches",
            "replay_source_evidence_hash_matches",
            "stale_hash_block_status",
            "client_ready_document_block_status",
            "forbidden_ai_action_block_status",
        ),
    )


def build_decision_path_summaries(parity: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        path_name: select_fields(
            dict_at(parity, path_name),
            (
                "top_level_status",
                "decision_status",
                "primary_reason_code",
                "recommended_next_action",
                "approval_requirement_types",
            ),
        )
        for path_name in ("ready_decision", "review_decision", "blocked_decision")
    }


def build_alternatives_path_summaries(parity: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        path_name: select_fields(
            dict_at(parity, path_name),
            (
                "requested_objectives",
                "feasible_count",
                "feasible_with_review_count",
                "rejected_count",
                "selected_alternative_id",
                "selected_rank",
                "top_ranked_objective",
                "top_ranked_reason_codes",
                "rejected_reason_codes",
            ),
        )
        for path_name in (
            "noop_alternatives",
            "concentration_alternatives",
            "cash_raise_alternatives",
            "cross_currency_alternatives",
            "restricted_product_alternatives",
        )
    }


def build_degraded_runtime_summary(degraded: dict[str, Any]) -> dict[str, Any]:
    return {
        "risk_drill_portfolio": degraded.get("risk_drill_portfolio"),
        "risk_degraded_reason": degraded.get("risk_degraded_reason"),
        "core_degraded_reason": degraded.get("core_degraded_reason"),
        "fallback_mode": degraded.get("fallback_mode"),
        "insufficient_evidence_decision": select_fields(
            dict_at(degraded, "insufficient_evidence_decision"),
            (
                "top_level_status",
                "decision_status",
                "primary_reason_code",
                "recommended_next_action",
            ),
        ),
        "risk_unavailable_alternatives": select_fields(
            dict_at(degraded, "risk_unavailable_alternatives"),
            ("requested_objectives", "rejected_count", "rejected_reason_codes"),
        ),
        "core_unavailable_alternatives": select_fields(
            dict_at(degraded, "core_unavailable_alternatives"),
            ("requested_objectives", "rejected_count", "rejected_reason_codes"),
        ),
    }
