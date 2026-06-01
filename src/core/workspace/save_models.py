from typing import Optional

from pydantic import BaseModel, Field

from src.core.workspace.session_models import WorkspaceSession
from src.core.workspace.version_models import WorkspaceSavedVersion


class WorkspaceSaveRequest(BaseModel):
    saved_by: str = Field(
        description="Actor identifier saving the current workspace version.",
        examples=["advisor_123"],
    )
    version_label: Optional[str] = Field(
        default=None,
        description="Optional advisor-facing label for the saved workspace version.",
        examples=["Initial sandbox draft"],
    )


class WorkspaceSaveResponse(BaseModel):
    workspace: WorkspaceSession = Field(
        description="Workspace session after the save operation.",
    )
    saved_version: WorkspaceSavedVersion = Field(
        description="Saved workspace version created by the request.",
    )


class WorkspaceSavedVersionListResponse(BaseModel):
    workspace_id: str = Field(
        description="Workspace session identifier.",
        examples=["aws_001"],
    )
    saved_versions: list[WorkspaceSavedVersion] = Field(
        description="Saved workspace versions available for compare and resume workflows.",
    )


class WorkspaceResumeRequest(BaseModel):
    actor_id: str = Field(
        description="Actor identifier resuming a saved workspace version.",
        examples=["advisor_123"],
    )
    workspace_version_id: str = Field(
        description="Saved workspace version identifier to restore into the current draft.",
        examples=["awv_001"],
    )
