from uuid import uuid4


def new_proposal_id() -> str:
    return _new_prefixed_id("pp")


def new_proposal_version_id() -> str:
    return _new_prefixed_id("ppv")


def new_workflow_event_id() -> str:
    return _new_prefixed_id("pwe")


def new_async_operation_id() -> str:
    return _new_prefixed_id("pop")


def new_execution_request_id() -> str:
    return _new_prefixed_id("pex")


def new_approval_id() -> str:
    return _new_prefixed_id("pap")


def new_report_request_id() -> str:
    return _new_prefixed_id("prr")


def _new_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"
