from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.bank_demo_proof.model_common import (
    RFC28_ARTIFACT_URI_MAX_LENGTH,
    RFC28_CLAIM_TEXT_MAX_LENGTH,
    RFC28_IDENTIFIER_MAX_LENGTH,
    RFC28_MAX_PROOF_ASSETS,
    RFC28_MAX_REF_LIST_ITEMS,
    RFC28_MAX_REPOSITORY_SHAS,
    ClientReadyProofPosture,
    contains_sensitive_technical_term,
    normalize_ref_list,
    normalize_required_text,
)
from src.core.bank_demo_proof.proof_asset_models import ProofAsset
from src.core.bank_demo_proof.validation import normalize_lotus_advise_contract_ref


class AdvisoryBankDemoProofPack(BaseModel):
    contract_name: Literal["AdvisoryBankDemoProofPack"] = Field(default="AdvisoryBankDemoProofPack")
    contract_version: Literal["v1"] = Field(default="v1")
    proof_pack_id: str = Field(
        description="Stable proof-pack identifier.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    scenario_id: str = Field(
        description="Governed demo scenario identifier.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    primary_portfolio_id: str = Field(
        description="Canonical portfolio proven by this pack.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    proof_marker: str = Field(
        description="Proof marker emitted by successful proof capture.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    generated_at: datetime = Field(description="UTC proof-pack generation timestamp.")
    correlation_id: str = Field(
        description="Correlation id for proof-pack generation.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    client_ready_posture: ClientReadyProofPosture = Field(
        description="Client-ready publication posture proven by this pack."
    )
    repository_shas: dict[str, str] = Field(
        min_length=1,
        max_length=RFC28_MAX_REPOSITORY_SHAS,
        description="Repository commit SHAs included in the proof pack.",
    )
    evidence_markers: list[str] = Field(
        min_length=1,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Evidence markers observed during proof capture.",
    )
    scenario_contract_ref: str = Field(
        description="Scenario contract reference.",
        max_length=RFC28_ARTIFACT_URI_MAX_LENGTH,
    )
    supported_claim_register_ref: str = Field(
        description="Supported-claim register reference.",
        max_length=RFC28_ARTIFACT_URI_MAX_LENGTH,
    )
    source_product_refs: list[str] = Field(
        min_length=1,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Active data products used as proof sources.",
    )
    assets: list[ProofAsset] = Field(
        max_length=RFC28_MAX_PROOF_ASSETS,
        description="Proof asset index.",
    )
    unsupported_boundaries: list[str] = Field(
        min_length=1,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Unsupported or blocked capabilities proven by the pack.",
    )

    @field_validator(
        "proof_pack_id",
        "scenario_id",
        "primary_portfolio_id",
        "proof_marker",
        "correlation_id",
    )
    @classmethod
    def _proof_pack_identifiers_must_be_bounded(cls, value: str) -> str:
        return normalize_required_text(value, error_code="proof-pack identifier is required")

    @field_validator("scenario_contract_ref", "supported_claim_register_ref")
    @classmethod
    def _proof_pack_contract_refs_must_be_safe(cls, value: str) -> str:
        return normalize_lotus_advise_contract_ref(value, field_name="proof-pack contract ref")

    @field_validator("generated_at")
    @classmethod
    def _generated_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
            raise ValueError("proof-pack generated_at must be timezone-aware UTC")
        return value

    @field_validator("repository_shas")
    @classmethod
    def _repository_shas_must_be_bounded(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for repository, sha in value.items():
            repository_name = normalize_required_text(
                str(repository),
                error_code="repository name is required",
            )
            if len(repository_name) > RFC28_IDENTIFIER_MAX_LENGTH:
                raise ValueError("repository name is too long")
            if contains_sensitive_technical_term(repository_name):
                raise ValueError("repository name cannot contain sensitive technical detail")
            if repository_name in normalized:
                raise ValueError("repository names must be unique after normalization")
            repository_sha = normalize_required_text(
                str(sha),
                error_code="repository sha is required",
            )
            if len(repository_sha) > RFC28_IDENTIFIER_MAX_LENGTH:
                raise ValueError("repository sha is too long")
            if contains_sensitive_technical_term(repository_sha):
                raise ValueError("repository sha cannot contain sensitive technical detail")
            normalized[repository_name] = repository_sha
        return normalized

    @field_validator("evidence_markers", "source_product_refs")
    @classmethod
    def _proof_pack_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        return normalize_ref_list(value, field_name="proof-pack refs")

    @field_validator("unsupported_boundaries")
    @classmethod
    def _unsupported_boundaries_must_be_business_safe(cls, value: list[str]) -> list[str]:
        normalized = normalize_ref_list(
            value,
            field_name="proof-pack unsupported_boundaries",
            max_item_length=RFC28_CLAIM_TEXT_MAX_LENGTH,
        )
        for boundary in normalized:
            if contains_sensitive_technical_term(boundary):
                raise ValueError("unsupported boundary cannot contain sensitive technical detail")
        return normalized

    @model_validator(mode="after")
    def _proof_pack_must_include_marker_and_block_unsafe_assets(self) -> AdvisoryBankDemoProofPack:
        if self.proof_marker not in self.evidence_markers:
            raise ValueError("proof_marker must be present in evidence_markers")
        asset_ids = [asset.asset_id for asset in self.assets]
        if len(set(asset_ids)) != len(asset_ids):
            raise ValueError("proof-pack asset ids must be unique")
        return self
