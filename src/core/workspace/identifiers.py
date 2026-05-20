from uuid import uuid4


def new_workspace_id() -> str:
    return _new_prefixed_id("aws")


def new_workspace_trade_id() -> str:
    return _new_prefixed_id("wtd")


def new_workspace_cash_flow_id() -> str:
    return _new_prefixed_id("wcf")


def new_workspace_version_id() -> str:
    return _new_prefixed_id("awv")


def _new_prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"
