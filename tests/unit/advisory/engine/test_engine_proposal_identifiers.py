import re

from src.core.proposals.identifiers import (
    new_approval_id,
    new_async_operation_id,
    new_execution_request_id,
    new_proposal_id,
    new_proposal_version_id,
    new_report_request_id,
    new_workflow_event_id,
)


def test_proposal_identifier_factories_use_governed_prefixes():
    identifiers = {
        "pp": new_proposal_id(),
        "ppv": new_proposal_version_id(),
        "pwe": new_workflow_event_id(),
        "pop": new_async_operation_id(),
        "pex": new_execution_request_id(),
        "pap": new_approval_id(),
        "prr": new_report_request_id(),
    }

    for prefix, identifier in identifiers.items():
        assert re.fullmatch(rf"{prefix}_[0-9a-f]{{12}}", identifier)
