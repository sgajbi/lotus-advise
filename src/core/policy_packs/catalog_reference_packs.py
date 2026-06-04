from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.policy_packs.catalog_definitions import CATALOG_CONTRACT_VERSION

_REFERENCE_PACKS: list[dict[str, Any]] = [
    {
        "policy_pack_id": "GLOBAL_PRIVATE_BANKING_BASELINE",
        "policy_version": "2026.05",
        "policy_family": "GLOBAL_PRIVATE_BANKING",
        "display_name": "Global Private Banking Baseline",
        "jurisdiction_scope": ["GLOBAL"],
        "booking_center_code_scope": ["GLOBAL"],
        "legal_entity_scope": ["REFERENCE"],
        "client_segment_scope": ["PRIVATE_BANKING"],
        "product_scope": ["MULTI_ASSET"],
        "effective_from": "2026-05-01",
        "effective_to": "3999-12-31",
        "activation_state": "ACTIVE",
        "owner_role": "ADVISORY_POLICY_STEWARD",
        "maker_checker_required": False,
        "schema_version": CATALOG_CONTRACT_VERSION,
        "applicability": {
            "jurisdiction_scope": ["GLOBAL"],
            "booking_center_code_scope": ["GLOBAL"],
            "legal_entity_scope": ["REFERENCE"],
            "client_segment_scope": ["PRIVATE_BANKING"],
            "product_scope": ["MULTI_ASSET"],
        },
        "source_requirements": [
            "client_classification",
            "mandate_objectives",
            "mandate_restrictions",
            "holdings_cash_market_data",
            "product_eligibility",
            "risk_policy_metrics",
        ],
        "rules": [
            {
                "rule_id": "GLOBAL_SOURCE_READINESS_REQUIRED",
                "severity": "BLOCKING",
                "required_evidence_fields": [
                    "policy_source_readiness.overall_posture",
                    "policy_source_readiness.source_authority",
                ],
                "source_gap_handling": "PENDING_REVIEW_OR_BLOCKED",
                "outcome_mapping": "NO_POSITIVE_POLICY_OUTCOME_WITH_MISSING_SOURCE_EVIDENCE",
            },
            {
                "rule_id": "GLOBAL_MANDATE_RESTRICTIONS_REVIEW",
                "severity": "REVIEW_REQUIRED",
                "required_evidence_fields": [
                    "core_mandate_objectives_restrictions",
                ],
                "source_gap_handling": "PENDING_REVIEW_OR_BLOCKED",
                "outcome_mapping": "MANDATE_RESTRICTIONS_REQUIRE_ADVISOR_REVIEW",
            },
        ],
        "disclosure_templates": [],
        "consent_templates": [],
        "approval_routes": [
            {
                "route_id": "ADVISOR_REVIEW",
                "owner_role": "ADVISOR",
                "review_sla": "P2D",
            }
        ],
        "sample_fixture_refs": [
            "PB_SG_GLOBAL_BAL_001",
            "fixtures/policy-packs/global-private-banking-baseline.json",
        ],
    },
    {
        "policy_pack_id": "SG_PRIVATE_BANKING_REFERENCE",
        "policy_version": "2026.05",
        "policy_family": "SG_PRIVATE_BANKING",
        "display_name": "Singapore Private Banking Reference",
        "jurisdiction_scope": ["SG"],
        "booking_center_code_scope": ["SG"],
        "legal_entity_scope": ["REFERENCE"],
        "client_segment_scope": ["ACCREDITED_INVESTOR", "PRIVATE_BANKING"],
        "product_scope": ["MULTI_ASSET", "STRUCTURED_PRODUCT", "PRIVATE_ASSET"],
        "effective_from": "2026-05-01",
        "effective_to": "3999-12-31",
        "activation_state": "DRAFT",
        "owner_role": "ADVISORY_POLICY_STEWARD",
        "maker_checker_required": True,
        "schema_version": CATALOG_CONTRACT_VERSION,
        "applicability": {
            "jurisdiction_scope": ["SG"],
            "booking_center_code_scope": ["SG"],
            "legal_entity_scope": ["REFERENCE"],
            "client_segment_scope": ["ACCREDITED_INVESTOR", "PRIVATE_BANKING"],
            "product_scope": ["MULTI_ASSET", "STRUCTURED_PRODUCT", "PRIVATE_ASSET"],
        },
        "source_requirements": [
            "household_id",
            "account_id",
            "mandate_id",
            "client_classification",
            "product_eligibility",
            "target_market",
            "product_complexity",
            "risk_policy_metrics",
        ],
        "rules": [
            {
                "rule_id": "SG_AI_PRODUCT_ELIGIBILITY_REVIEW",
                "severity": "BLOCKING",
                "required_evidence_fields": [
                    "core_product_eligibility_target_market_complexity",
                    "core_client_profile_classification",
                ],
                "source_gap_handling": "BLOCKED",
                "outcome_mapping": "ELIGIBILITY_REVIEW_REQUIRED",
            },
            {
                "rule_id": "SG_COMPLEX_PRODUCT_DISCLOSURE_REVIEW",
                "severity": "REVIEW_REQUIRED",
                "required_evidence_fields": [
                    "private_asset_or_structured_product_flag",
                    "risk_policy_metrics",
                ],
                "source_gap_handling": "PENDING_REVIEW",
                "outcome_mapping": "DISCLOSURE_AND_CONSENT_REVIEW_REQUIRED",
            },
            {
                "rule_id": "SG_BEST_INTEREST_COST_REVIEW",
                "severity": "REVIEW_REQUIRED",
                "required_evidence_fields": [
                    "fee_cost_tax_friction_evidence",
                ],
                "source_gap_handling": "PENDING_REVIEW",
                "outcome_mapping": "BEST_INTEREST_COST_REASONABLENESS_REVIEW_REQUIRED",
            },
            {
                "rule_id": "SG_CONFLICT_REVIEW",
                "severity": "REVIEW_REQUIRED",
                "required_evidence_fields": [
                    "conflict_evidence",
                    "product_document_evidence",
                ],
                "source_gap_handling": "PENDING_REVIEW",
                "outcome_mapping": "CONFLICT_AND_DISCLOSURE_REVIEW_REQUIRED",
            },
        ],
        "disclosure_templates": [
            {
                "template_id": "SG_COMPLEX_PRODUCT_DISCLOSURE",
                "template_version": "2026.05",
                "audience": "INTERNAL_REVIEW",
            }
        ],
        "consent_templates": [
            {
                "template_id": "SG_COMPLEX_PRODUCT_CONSENT",
                "template_version": "2026.05",
                "audience": "INTERNAL_REVIEW",
            }
        ],
        "approval_routes": [
            {
                "route_id": "INVESTMENT_COUNSELLOR_REVIEW",
                "owner_role": "INVESTMENT_COUNSELLOR",
                "review_sla": "P1D",
            },
            {
                "route_id": "SUPERVISORY_REVIEW",
                "owner_role": "SUPERVISOR",
                "review_sla": "P2D",
            },
        ],
        "sample_fixture_refs": [
            "PB_SG_GLOBAL_BAL_001",
            "fixtures/policy-packs/sg-private-banking-reference.json",
        ],
    },
]


def reference_policy_packs() -> list[dict[str, Any]]:
    return deepcopy(_REFERENCE_PACKS)
