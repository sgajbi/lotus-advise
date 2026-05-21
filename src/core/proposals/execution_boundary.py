from typing import Dict

ADVISORY_EXECUTION_ROLE = "HANDOFF_REQUEST_AND_STATUS_RECONCILIATION"
EXECUTION_SYSTEM_OF_RECORD = "DOWNSTREAM_EXECUTION_PROVIDER"
EXECUTION_OWNERSHIP_BOUNDARY = "DOWNSTREAM_EXECUTION_SYSTEM_OF_RECORD"


def execution_ownership_boundary() -> Dict[str, str]:
    return {
        "advisory_role": ADVISORY_EXECUTION_ROLE,
        "execution_system_of_record": EXECUTION_SYSTEM_OF_RECORD,
        "ownership_boundary": EXECUTION_OWNERSHIP_BOUNDARY,
    }
