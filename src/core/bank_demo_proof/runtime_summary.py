from __future__ import annotations

from typing import Any

from src.core.bank_demo_proof.models import RFC28_CANONICAL_SCENARIO_ID


def sanitize_live_runtime_summary(live_runtime_payload: dict[str, Any]) -> dict[str, Any]:
    parity = dict_at(live_runtime_payload, "parity")
    degraded = dict_at(live_runtime_payload, "degraded")
    return {
        "scenario_id": RFC28_CANONICAL_SCENARIO_ID,
        "primary_portfolio_id": value_at(
            live_runtime_payload,
            "parity.complete_issuer_portfolio",
        ),
        "proposal_lifecycle": {
            "sync_state": parity.get("lifecycle_current_state"),
            "sync_latest_version": parity.get("lifecycle_latest_version_no"),
            "async_state": parity.get("async_lifecycle_current_state"),
            "async_latest_version": parity.get("async_lifecycle_latest_version_no"),
            "execution_handoff_status": parity.get("execution_handoff_status"),
            "execution_terminal_status": parity.get("execution_terminal_status"),
            "report_status": parity.get("report_status"),
        },
        "workspace_rationale": {
            "initial_run_recorded": bool(parity.get("workspace_rationale_initial_run_id")),
            "replacement_run_recorded": bool(parity.get("workspace_rationale_replacement_run_id")),
            "review_state": parity.get("workspace_rationale_review_state"),
            "supportability_status": parity.get("workspace_rationale_supportability_status"),
        },
        "proposal_narrative": select_fields(
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
        ),
        "proposal_memo": select_fields(
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
        ),
        "proposal_policy": select_fields(
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
        ),
        "decision_paths": {
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
        },
        "alternatives_paths": {
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
        },
        "degraded_runtime": {
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
        },
    }


def dict_at(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"RFC0028_BACKEND_PROOF_FIELD_MISSING: {key}")
    return value


def value_at(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"RFC0028_BACKEND_PROOF_FIELD_MISSING: {dotted_path}")
        current = current[part]
    return current


def select_fields(payload: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: payload.get(key) for key in keys}
