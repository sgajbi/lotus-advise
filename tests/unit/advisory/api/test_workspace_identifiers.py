import re

from src.core.workspace.identifiers import (
    new_workspace_cash_flow_id,
    new_workspace_id,
    new_workspace_trade_id,
    new_workspace_version_id,
)


def test_workspace_identifier_factories_use_governed_prefixes():
    identifiers = {
        "aws": new_workspace_id(),
        "wtd": new_workspace_trade_id(),
        "wcf": new_workspace_cash_flow_id(),
        "awv": new_workspace_version_id(),
    }

    for prefix, identifier in identifiers.items():
        assert re.fullmatch(rf"{prefix}_[0-9a-f]{{12}}", identifier)
