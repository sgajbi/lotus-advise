import sys

import pytest

from src.api.routers.proposals_lifecycle_routes import _raise_transition_http_exception
from src.api.services import advisory_simulation_service


def test_raise_transition_http_exception_re_raises_unknown_exception():
    with pytest.raises(ValueError, match="unexpected"):
        _raise_transition_http_exception(ValueError("unexpected"))


def test_main_override_returns_none_when_main_module_not_loaded(monkeypatch):
    monkeypatch.delitem(sys.modules, "src.api.main", raising=False)
    assert advisory_simulation_service._main_override("run_proposal_simulation") is None
