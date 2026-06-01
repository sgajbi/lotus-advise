from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.bank_demo_proof.model_common import (
    RFC28_BUSINESS_TITLE_MAX_LENGTH,
    RFC28_CLAIM_TEXT_MAX_LENGTH,
    RFC28_IDENTIFIER_MAX_LENGTH,
    RFC28_MAX_REF_LIST_ITEMS,
    contains_sensitive_technical_term,
    normalize_ref_list,
    normalize_required_text,
)


class DemoScenarioStep(BaseModel):
    step_id: str = Field(
        description="Stable scenario step identifier.",
        examples=["advisor_cockpit"],
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    title: str = Field(
        description="Business-facing scenario step title.",
        max_length=RFC28_BUSINESS_TITLE_MAX_LENGTH,
    )
    owner_repository: str = Field(
        description="Repository that owns the step evidence.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    required_evidence_refs: list[str] = Field(
        default_factory=list,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Evidence references required before this step can be claimed.",
    )
    required_workbench_panels: list[str] = Field(
        default_factory=list,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description=(
            "Workbench panel identifiers required when this step is a product-surface step."
        ),
    )

    @field_validator("step_id", "owner_repository")
    @classmethod
    def _step_identifiers_must_be_bounded(cls, value: str) -> str:
        return normalize_required_text(value, error_code="scenario step identifier is required")

    @field_validator("title")
    @classmethod
    def _step_title_must_be_business_safe(cls, value: str) -> str:
        normalized = normalize_required_text(
            value,
            error_code="scenario step title is required",
        )
        if contains_sensitive_technical_term(normalized):
            raise ValueError("scenario step title cannot contain sensitive technical detail")
        return normalized

    @field_validator("required_evidence_refs", "required_workbench_panels")
    @classmethod
    def _step_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        return normalize_ref_list(value, field_name="scenario step refs")


class AdvisoryDemoScenarioContract(BaseModel):
    contract_name: Literal["AdvisoryDemoScenarioContract"] = Field(
        default="AdvisoryDemoScenarioContract"
    )
    contract_version: Literal["v1"] = Field(default="v1")
    scenario_id: str = Field(
        description="Governed bank-demo scenario identifier.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    primary_portfolio_id: str = Field(
        description="Canonical portfolio identifier.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    governed_as_of_date: date = Field(description="Governed scenario as-of date.")
    proof_marker: str = Field(
        description="Evidence marker emitted by successful proof capture.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    required_evidence_markers: list[str] = Field(
        min_length=1,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Evidence markers that must appear in a successful proof pack.",
    )
    required_source_products: list[str] = Field(
        min_length=1,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Active Advise data products used as source evidence.",
    )
    unsupported_boundaries: list[str] = Field(
        min_length=1,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Capability boundaries that must not be overclaimed in the demo.",
    )
    steps: list[DemoScenarioStep] = Field(
        min_length=1,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Business scenario steps in demo order.",
    )

    @field_validator("scenario_id", "primary_portfolio_id", "proof_marker")
    @classmethod
    def _scenario_identifiers_must_be_bounded(cls, value: str) -> str:
        return normalize_required_text(value, error_code="scenario identifier is required")

    @field_validator("required_evidence_markers", "required_source_products")
    @classmethod
    def _scenario_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        return normalize_ref_list(value, field_name="scenario refs")

    @field_validator("unsupported_boundaries")
    @classmethod
    def _scenario_boundaries_must_be_business_safe(cls, value: list[str]) -> list[str]:
        normalized = normalize_ref_list(
            value,
            field_name="scenario unsupported_boundaries",
            max_item_length=RFC28_CLAIM_TEXT_MAX_LENGTH,
        )
        for boundary in normalized:
            if contains_sensitive_technical_term(boundary):
                raise ValueError("scenario unsupported boundary cannot contain sensitive detail")
        return normalized

    @model_validator(mode="after")
    def _proof_marker_must_be_required(self) -> AdvisoryDemoScenarioContract:
        if self.proof_marker not in self.required_evidence_markers:
            raise ValueError("proof_marker must be present in required_evidence_markers")
        step_ids = [step.step_id for step in self.steps]
        if len(set(step_ids)) != len(step_ids):
            raise ValueError("scenario step_id values must be unique")
        return self
