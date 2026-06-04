from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProposalArtifactEvidenceInputs(BaseModel):
    portfolio_snapshot: Dict[str, Any] = Field(
        description="Original portfolio snapshot input payload."
    )
    market_data_snapshot: Dict[str, Any] = Field(
        description="Original market-data snapshot input payload."
    )
    shelf_entries: List[Dict[str, Any]] = Field(description="Original shelf entries input payload.")
    options: Dict[str, Any] = Field(description="Original request options payload.")
    proposed_cash_flows: List[Dict[str, Any]] = Field(
        description="Original proposed cash-flow payload rows."
    )
    proposed_trades: List[Dict[str, Any]] = Field(
        description="Original proposed trade payload rows."
    )
    reference_model: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Original optional reference model payload.",
    )


class ProposalArtifactEngineOutputs(BaseModel):
    proposal_result: Dict[str, Any] = Field(
        description="Full proposal simulation output payload used to build artifact."
    )


class ProposalArtifactHashes(BaseModel):
    request_hash: str = Field(
        description="Canonical request hash from proposal lineage.",
        examples=["sha256:4e2baf..."],
    )
    artifact_hash: str = Field(
        description="Canonical artifact hash excluding volatile fields.",
        examples=["sha256:10ffab..."],
    )


class ProposalArtifactEvidenceBundle(BaseModel):
    inputs: ProposalArtifactEvidenceInputs = Field(description="Input evidence payloads.")
    engine_outputs: ProposalArtifactEngineOutputs = Field(
        description="Engine output evidence payloads."
    )
    hashes: ProposalArtifactHashes = Field(description="Request and artifact hashes.")
    engine_version: str = Field(
        description="Engine version captured in proposal lineage.",
        examples=["0.1.0"],
    )
