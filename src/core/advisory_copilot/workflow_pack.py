from __future__ import annotations

from src.core.advisory_copilot.catalog import get_copilot_action_definition
from src.core.advisory_copilot.models import CopilotActionFamily

WORKFLOW_PACK_EXECUTION_AUTHORITY = "lotus-ai"
WORKFLOW_PACK_CALLER_APP = "lotus-advise"


def workflow_pack_id_for_action(action_family: CopilotActionFamily) -> str:
    return get_copilot_action_definition(action_family).workflow_pack_id


def workflow_pack_version_for_action(action_family: CopilotActionFamily) -> str:
    return get_copilot_action_definition(action_family).workflow_pack_version

